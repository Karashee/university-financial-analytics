import logging

import pandas as pd

from app.ml.features import (
    build_isolation_forest_features,
    build_linear_regression_features,
    get_if_feature_columns,
    get_lr_feature_columns,
)

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


# --- Linear Regression feature engineering ---

DEPT_MONTHLY_VALUES = {
    "DEPT01": [1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0],
    "DEPT02": [2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0],
    "DEPT03": [3000.0, 3100.0, 3200.0, 3300.0, 3400.0, 3500.0],
}


def make_lr_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    """3 departments x 6 months, 2 transaction rows per dept-month.
    DEPT01 month 3 is flagged as ground-truth anomaly. DEPT03 has no budget row."""
    rows = []
    for dept, values in DEPT_MONTHLY_VALUES.items():
        for month_index, value in enumerate(values, start=1):
            for txn_num in range(2):
                rows.append({
                    "transaction_id": f"{dept}-{month_index}-{txn_num}",
                    "department_id": dept,
                    "fiscal_year": 2023,
                    "fiscal_month": month_index,
                    "monthly_expenditure": value,
                    "historical_average_expenditure": value * 0.9,
                    "expenditure_growth_rate": 0.05,
                    "is_anomaly_ground_truth": 1 if (dept == "DEPT01" and month_index == 3) else 0,
                })
    df = pd.DataFrame(rows)

    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 500_000.0},
        {"department_id": "DEPT02", "fiscal_year": 2023, "budget_allocation": 600_000.0},
        # DEPT03 intentionally has no matching budget row.
    ])

    return df, budgets_df


def test_lr_x_has_expected_base_columns():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    for column in [
        "fiscal_month", "fiscal_year", "historical_average_expenditure",
        "expenditure_growth_rate", "budget_allocation", "lag_1_expenditure",
    ]:
        assert column in X_df.columns
    assert any(column.startswith("dept_") for column in X_df.columns)


def test_lr_budget_allocation_present_and_numeric_in_x():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    assert pd.api.types.is_numeric_dtype(X_df["budget_allocation"])


def test_lr_monthly_expenditure_absent_from_x_present_as_y():
    df, budgets_df = make_lr_dataset()
    X_df, y_series = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    assert "monthly_expenditure" not in X_df.columns
    assert len(y_series) == len(X_df)


def test_lr_lag_1_month_2_equals_month_1_value():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    row = X_df[(X_df["dept_DEPT02"] == True) & (X_df["fiscal_month"] == 2)]
    assert row.iloc[0]["lag_1_expenditure"] == 2000.0


def test_lr_lag_1_month_1_equals_department_mean_not_nan():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    row = X_df[(X_df["dept_DEPT02"] == True) & (X_df["fiscal_month"] == 1)]
    expected_mean = sum(DEPT_MONTHLY_VALUES["DEPT02"]) / len(DEPT_MONTHLY_VALUES["DEPT02"])
    assert row.iloc[0]["lag_1_expenditure"] == expected_mean
    assert not pd.isna(row.iloc[0]["lag_1_expenditure"])


def test_lr_lag_year_boundary_rollover_dec_to_jan():
    rows = [
        {"transaction_id": "ROLL-2023-11", "department_id": "DEPT99", "fiscal_year": 2023,
         "fiscal_month": 11, "monthly_expenditure": 5000.0,
         "historical_average_expenditure": 4500.0, "expenditure_growth_rate": 0.02,
         "is_anomaly_ground_truth": 0},
        {"transaction_id": "ROLL-2023-12", "department_id": "DEPT99", "fiscal_year": 2023,
         "fiscal_month": 12, "monthly_expenditure": 5500.0,
         "historical_average_expenditure": 4950.0, "expenditure_growth_rate": 0.02,
         "is_anomaly_ground_truth": 0},
        {"transaction_id": "ROLL-2024-01", "department_id": "DEPT99", "fiscal_year": 2024,
         "fiscal_month": 1, "monthly_expenditure": 6000.0,
         "historical_average_expenditure": 5400.0, "expenditure_growth_rate": 0.02,
         "is_anomaly_ground_truth": 0},
    ]
    df = pd.DataFrame(rows)
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT99", "fiscal_year": 2023, "budget_allocation": 100_000.0},
        {"department_id": "DEPT99", "fiscal_year": 2024, "budget_allocation": 110_000.0},
    ])

    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    jan_2024_row = X_df[(X_df["fiscal_year"] == 2024) & (X_df["fiscal_month"] == 1)]
    assert jan_2024_row.iloc[0]["lag_1_expenditure"] == 5500.0


def test_lr_missing_budget_allocation_is_nan_and_logs_warning(caplog):
    df, budgets_df = make_lr_dataset()
    with caplog.at_level(logging.WARNING):
        X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)

    dept03_rows = X_df[X_df["dept_DEPT03"] == True]
    assert len(dept03_rows) == 6
    assert dept03_rows["budget_allocation"].isna().all()
    assert any("budget_allocation" in record.message for record in caplog.records)


def test_lr_exclude_anomalies_removes_flagged_rows():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=True)
    dept01_month3 = X_df[(X_df["dept_DEPT01"] == True) & (X_df["fiscal_month"] == 3)]
    assert len(dept01_month3) == 0


def test_lr_x_and_y_have_same_length():
    df, budgets_df = make_lr_dataset()
    X_df, y_series = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    assert len(X_df) == len(y_series)


def test_get_lr_feature_columns_matches_x_columns():
    df, budgets_df = make_lr_dataset()
    X_df, _ = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    assert get_lr_feature_columns(X_df) == X_df.columns.tolist()
