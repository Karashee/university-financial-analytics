"""Feature engineering for the Isolation Forest and Linear Regression models."""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

VENDOR_RISK_SCORES = {
    "Unregistered Vendor": 3,
    "Regulatory Body": 0,
    "Internal Personnel Cost": 0,
    # any vendor_category not in this dict defaults to 1
}

_BASE_NUMERIC_COLUMNS = [
    "transaction_amount",
    "budget_utilization_percentage",
    "expenditure_variance",
    "historical_average_expenditure",
    "expenditure_growth_rate",
]

_VENDOR_COLUMNS = [
    "is_unregistered_vendor",
    "vendor_risk_score",
]

_RELATIONAL_COLUMNS = [
    "dept_category_frequency",
    "dept_vendor_frequency",
    "amount_z_within_dept",
    "amount_z_within_dept_category",
    "amount_over_dept_mean",
    "nearest_relative_gap",
]

_IF_FEATURE_COLUMNS = _BASE_NUMERIC_COLUMNS + _VENDOR_COLUMNS + _RELATIONAL_COLUMNS


def _nearest_relative_gap(amounts: pd.Series) -> pd.Series:
    """
    For each amount, the smallest relative distance to another amount in the
    same group. Near-duplicate payments produce a value close to zero, which is
    what makes a repeated payment separable from an ordinary one of the same
    size.
    """
    values = amounts.to_numpy(dtype=float)
    if len(values) < 2:
        return pd.Series(np.ones(len(values)), index=amounts.index)

    order = np.argsort(values)
    ordered = values[order]
    gaps = np.full(len(values), np.inf)

    for position in range(len(ordered)):
        denominator = max(ordered[position], 1.0)
        if position > 0:
            gaps[position] = min(
                gaps[position],
                abs(ordered[position] - ordered[position - 1]) / denominator,
            )
        if position < len(ordered) - 1:
            gaps[position] = min(
                gaps[position],
                abs(ordered[position + 1] - ordered[position]) / denominator,
            )

    result = np.ones(len(values))
    result[order] = gaps
    return pd.Series(result, index=amounts.index)


def build_isolation_forest_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the 13-column feature set used by the Isolation Forest model.

    Five base numeric columns and two vendor-derived columns describe each
    transaction in isolation. Six relational columns place the transaction in
    the context of its own department and expenditure category, which is what
    allows the model to reach irregularities that are ordinary in every
    individual field and unusual only in combination - a department paying for
    something outside its function, or an amount that is unremarkable across
    the institution but extreme for the unit that spent it.

    Requires department_id and expenditure_category in addition to the columns
    used by the base features.

    Drops rows where any of the 5 base numeric columns are null, retains the
    original DataFrame index, and never includes ground-truth anomaly labels.
    """
    result = df[_BASE_NUMERIC_COLUMNS].copy()

    result["is_unregistered_vendor"] = (
        df["vendor_category"] == "Unregistered Vendor"
    ).astype(int)
    result["vendor_risk_score"] = (
        df["vendor_category"].map(VENDOR_RISK_SCORES).fillna(1).astype(int)
    )

    amount = df["transaction_amount"]
    by_dept = df.groupby("department_id")["transaction_amount"]
    by_dept_category = df.groupby(
        ["department_id", "expenditure_category"]
    )["transaction_amount"]

    # How often this department uses this category, and this vendor type. A
    # department paying for something outside its function produces a low count
    # while remaining unremarkable in every other field.
    result["dept_category_frequency"] = by_dept_category.transform("size")
    result["dept_vendor_frequency"] = df.groupby(
        ["department_id", "vendor_category"]
    )["transaction_amount"].transform("size")

    # Amount relative to the department's own distribution, and to the
    # department-and-category distribution. Division guards against
    # single-member groups, whose standard deviation is zero or undefined.
    dept_std = by_dept.transform("std")
    result["amount_z_within_dept"] = (
        (amount - by_dept.transform("mean")) / dept_std.replace(0, np.nan)
    ).fillna(0.0)

    category_std = by_dept_category.transform("std")
    result["amount_z_within_dept_category"] = (
        (amount - by_dept_category.transform("mean")) / category_std.replace(0, np.nan)
    ).fillna(0.0)

    result["amount_over_dept_mean"] = (
        amount / by_dept.transform("mean").replace(0, np.nan)
    ).fillna(0.0)

    # Smallest relative distance to another payment of the same department and
    # category: near-duplicate payments sit close to zero.
    result["nearest_relative_gap"] = by_dept_category.transform(_nearest_relative_gap)

    result = result.dropna(subset=_BASE_NUMERIC_COLUMNS)

    return result[_IF_FEATURE_COLUMNS]


def get_if_feature_columns() -> list[str]:
    """Return the ordered list of Isolation Forest feature columns."""
    return list(_IF_FEATURE_COLUMNS)


def build_linear_regression_features(
    df: pd.DataFrame,
    budgets_df: pd.DataFrame,
    exclude_anomalies: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build monthly-level Linear Regression features and target.

    Aggregates transaction-level rows to one row per (department_id,
    fiscal_year, fiscal_month), joins in budget_allocation, adds a
    department-level lag-1 expenditure feature, and one-hot encodes
    department_id. Missing budget_allocation values are left as NaN (never
    silently filled) and logged as a warning.
    """
    working = df
    if exclude_anomalies:
        working = working[working["is_anomaly_ground_truth"] == 0]

    merged = working.merge(budgets_df, on=["department_id", "fiscal_year"], how="left")

    missing_budget_mask = merged["budget_allocation"].isna()
    if missing_budget_mask.any():
        missing_keys = (
            merged.loc[missing_budget_mask, ["department_id", "fiscal_year"]]
            .drop_duplicates()
            .to_dict(orient="records")
        )
        logger.warning(
            "Missing budget_allocation for %d (department_id, fiscal_year) pair(s): %s",
            len(missing_keys),
            missing_keys,
        )

    monthly = merged.groupby(
        ["department_id", "fiscal_year", "fiscal_month"],
        as_index=False,
    ).agg(
        monthly_expenditure=("monthly_expenditure", "first"),
        historical_average_expenditure=("historical_average_expenditure", "first"),
        expenditure_growth_rate=("expenditure_growth_rate", "first"),
        budget_allocation=("budget_allocation", "first"),
    )

    monthly = monthly.sort_values(
        ["department_id", "fiscal_year", "fiscal_month"]
    ).reset_index(drop=True)

    # Lag-1 expenditure: previous month's value within each department; the
    # first month of each department (no prior month) is filled with that
    # department's own mean monthly_expenditure, not the global mean.
    lag = monthly.groupby("department_id")["monthly_expenditure"].shift(1)
    department_mean = monthly.groupby("department_id")["monthly_expenditure"].transform("mean")
    monthly["lag_1_expenditure"] = lag.fillna(department_mean)

    # The lag above requires department-major ordering. Once it is computed,
    # re-sort chronologically so that a shuffle=False split holds out the most
    # recent months across all departments, rather than the last departments in
    # alphabetical order. Without this, the hold-out contains only DEPT06 and
    # DEPT07, and DEPT07 never appears in training at all.
    monthly = monthly.sort_values(
        ["fiscal_year", "fiscal_month", "department_id"]
    ).reset_index(drop=True)

    dept_dummies = pd.get_dummies(monthly["department_id"], prefix="dept", drop_first=False)
    monthly = pd.concat([monthly, dept_dummies], axis=1)

    feature_columns = [
        "fiscal_month",
        "fiscal_year",
        "historical_average_expenditure",
        "expenditure_growth_rate",
        "budget_allocation",
        "lag_1_expenditure",
    ] + list(dept_dummies.columns)

    y_series = monthly["monthly_expenditure"]
    valid_mask = y_series.notna()

    X_df = monthly.loc[valid_mask, feature_columns].reset_index(drop=True)
    y_series = y_series.loc[valid_mask].reset_index(drop=True)

    return X_df, y_series


def get_lr_feature_columns(X_df: pd.DataFrame) -> list[str]:
    """Return the ordered list of Linear Regression feature columns."""
    return X_df.columns.tolist()