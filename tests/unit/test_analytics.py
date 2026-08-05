import pandas as pd

from app.services.analytics_service import (
    compute_budget_utilization_dataframe,
    compute_growth_rate_dataframe,
    compute_variance_dataframe,
)
from app.services.reporting_service import compute_trend_summaries_dataframe


def test_total_transaction_amount_correct_group_totals():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 1000.0, "monthly_expenditure": 5000.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 2000.0, "monthly_expenditure": 5000.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 1500.0, "monthly_expenditure": 5000.0},
    ])
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 100000.0},
    ])

    result = compute_budget_utilization_dataframe(transactions_df, budgets_df)

    assert len(result) == 1
    assert result.iloc[0]["total_transaction_amount"] == 4500.0


def test_utilization_percentage_correct_formula():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 5000.0, "monthly_expenditure": 5000.0},
    ])
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 10000.0},
    ])

    result = compute_budget_utilization_dataframe(transactions_df, budgets_df)

    assert result.iloc[0]["utilization_percentage"] == 50.0


def test_utilization_percentage_exceeds_100_not_capped():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 15000.0, "monthly_expenditure": 15000.0},
    ])
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 10000.0},
    ])

    result = compute_budget_utilization_dataframe(transactions_df, budgets_df)

    assert result.iloc[0]["utilization_percentage"] == 150.0


def test_utilization_percentage_none_when_budget_allocation_zero():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 5000.0, "monthly_expenditure": 5000.0},
    ])
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 0.0},
    ])

    result = compute_budget_utilization_dataframe(transactions_df, budgets_df)

    assert result.iloc[0]["utilization_percentage"] is None


def test_monthly_expenditure_uses_first_value_not_sum():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 1000.0, "monthly_expenditure": 5000.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 2000.0, "monthly_expenditure": 5000.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 1500.0, "monthly_expenditure": 5000.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_category": "Admin", "transaction_amount": 500.0, "monthly_expenditure": 5000.0},
    ])
    budgets_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 100000.0},
    ])

    result = compute_budget_utilization_dataframe(transactions_df, budgets_df)

    assert result.iloc[0]["monthly_expenditure"] == 5000.0


def test_std_dev_variance_is_zero_not_nan_for_single_row_group():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "expenditure_variance": 500.0, "historical_average_expenditure": 5000.0},
    ])

    result = compute_variance_dataframe(transactions_df)

    assert result.iloc[0]["std_dev_variance"] == 0.0
    assert not pd.isna(result.iloc[0]["std_dev_variance"])


def test_avg_monthly_expenditure_uses_deduplicated_monthly_values():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "transaction_amount": 1000.0, "monthly_expenditure": 5000.0,
         "expenditure_growth_rate": 0.0, "expenditure_variance": 0.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "transaction_amount": 2000.0, "monthly_expenditure": 5000.0,
         "expenditure_growth_rate": 0.0, "expenditure_variance": 0.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "transaction_amount": 1500.0, "monthly_expenditure": 5000.0,
         "expenditure_growth_rate": 0.0, "expenditure_variance": 0.0},
        {"department_id": "DEPT01", "fiscal_year": 2023, "fiscal_month": 1,
         "transaction_amount": 500.0, "monthly_expenditure": 5000.0,
         "expenditure_growth_rate": 0.0, "expenditure_variance": 0.0},
    ])

    result = compute_trend_summaries_dataframe(transactions_df)

    assert result.iloc[0]["avg_monthly_expenditure"] == 5000.0


def test_growth_rate_summary_single_fiscal_year_returns_one_row_no_error():
    transactions_df = pd.DataFrame([
        {"department_id": "DEPT01", "fiscal_year": 2023, "expenditure_growth_rate": 0.05},
    ])

    result = compute_growth_rate_dataframe(transactions_df)

    assert len(result) == 1
    assert result.iloc[0]["avg_growth_rate"] == 0.05
