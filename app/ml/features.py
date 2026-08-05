"""Feature engineering for the Isolation Forest and Linear Regression models."""
import logging

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

_IF_FEATURE_COLUMNS = _BASE_NUMERIC_COLUMNS + [
    "is_unregistered_vendor",
    "vendor_risk_score",
]


def build_isolation_forest_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the 7-column feature set used by the Isolation Forest model.

    Drops rows where any of the 5 base numeric columns are null, retains the
    original DataFrame index, and never includes ground-truth anomaly labels.
    """
    result = df[_BASE_NUMERIC_COLUMNS].copy()
    result["is_unregistered_vendor"] = (df["vendor_category"] == "Unregistered Vendor").astype(int)
    result["vendor_risk_score"] = df["vendor_category"].map(VENDOR_RISK_SCORES).fillna(1).astype(int)

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
