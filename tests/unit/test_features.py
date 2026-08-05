import pandas as pd

from app.ml.features import build_isolation_forest_features, get_if_feature_columns

EXPECTED_COLUMNS = [
    "transaction_amount",
    "budget_utilization_percentage",
    "expenditure_variance",
    "historical_average_expenditure",
    "expenditure_growth_rate",
    "is_unregistered_vendor",
    "vendor_risk_score",
]


def make_transactions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "transaction_amount": [1000.0, 2000.0, 3000.0, 4000.0, None],
            "budget_utilization_percentage": [10.0, 20.0, 30.0, 40.0, 50.0],
            "expenditure_variance": [1.0, 2.0, 3.0, 4.0, 5.0],
            "historical_average_expenditure": [100.0, 200.0, 300.0, 400.0, 500.0],
            "expenditure_growth_rate": [0.1, 0.2, 0.3, 0.4, 0.5],
            "vendor_category": [
                "Unregistered Vendor",
                "Regulatory Body",
                "General Supplier",
                "Some Other Category",
                "Internal Personnel Cost",
            ],
            "is_anomaly_ground_truth": [1, 0, 0, 0, 1],
        },
        index=[10, 11, 12, 13, 14],
    )


def test_output_has_exactly_7_columns_in_order():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert list(result.columns) == EXPECTED_COLUMNS


def test_is_unregistered_vendor_flag():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert result.loc[10, "is_unregistered_vendor"] == 1
    assert result.loc[11, "is_unregistered_vendor"] == 0
    assert result.loc[12, "is_unregistered_vendor"] == 0
    assert result.loc[13, "is_unregistered_vendor"] == 0


def test_vendor_risk_score_values():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert result.loc[10, "vendor_risk_score"] == 3  # Unregistered Vendor
    assert result.loc[11, "vendor_risk_score"] == 0  # Regulatory Body
    assert result.loc[12, "vendor_risk_score"] == 1  # General Supplier (not in dict)
    assert result.loc[13, "vendor_risk_score"] == 1  # Some Other Category (not in dict)


def test_row_with_null_transaction_amount_excluded():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert 14 not in result.index
    assert len(result) == 4


def test_original_index_retained():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert list(result.index) == [10, 11, 12, 13]


def test_is_anomaly_ground_truth_not_in_output():
    df = make_transactions_df()
    result = build_isolation_forest_features(df)
    assert "is_anomaly_ground_truth" not in result.columns


def test_get_if_feature_columns_matches_output_order():
    assert get_if_feature_columns() == EXPECTED_COLUMNS
