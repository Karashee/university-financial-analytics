"""Feature engineering for the Isolation Forest anomaly detection model."""
import pandas as pd

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
