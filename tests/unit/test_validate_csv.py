import pandas as pd

from scripts.validate_csv import validate_dataframe


def make_valid_row(**overrides) -> dict:
    row = {
        "Transaction_ID": "TXN001",
        "Department_ID": "DEPT01",
        "Transaction_Date": "2023-01-15",
        "Expenditure_Category": "Administrative Operations",
        "Fiscal_Month": 1,
        "Fiscal_Year": 2023,
        "Monthly_Expenditure": 100000.0,
        "Historical_Average_Expenditure": 95000.0,
        "Expenditure_Variance": 5000.0,
        "Transaction_Amount": 5000.0,
        "Budget_Utilization_Percentage": 65.0,
    }
    row.update(overrides)
    return row


def test_rule1_pass():
    df = pd.DataFrame([make_valid_row(Budget_Utilization_Percentage=65.0)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 0
    assert result["valid_count"] == 1


def test_rule1_fail():
    df = pd.DataFrame([make_valid_row(Budget_Utilization_Percentage=105.0)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_1_UTILIZATION"


def test_rule1_boundary_pass():
    df = pd.DataFrame([
        make_valid_row(Transaction_ID="TXN001", Budget_Utilization_Percentage=0.0),
        make_valid_row(Transaction_ID="TXN002", Budget_Utilization_Percentage=100.0),
    ])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 0
    assert result["valid_count"] == 2


def test_rule2_pass():
    df = pd.DataFrame([make_valid_row(Transaction_Amount=5000)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 0


def test_rule2_fail_negative():
    df = pd.DataFrame([make_valid_row(Transaction_Amount=-200)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_2_AMOUNT"


def test_rule2_fail_zero():
    df = pd.DataFrame([make_valid_row(Transaction_Amount=0.0)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_2_AMOUNT"


def test_rule3_pass():
    df = pd.DataFrame([make_valid_row(
        Monthly_Expenditure=100000.0,
        Historical_Average_Expenditure=95000.0,
        Expenditure_Variance=5000.0,
    )])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 0


def test_rule3_fail():
    df = pd.DataFrame([make_valid_row(
        Monthly_Expenditure=100000.0,
        Historical_Average_Expenditure=95000.0,
        Expenditure_Variance=6000.0,
    )])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_3_VARIANCE"


def test_rule3_skipped_when_monthly_expenditure_null():
    df = pd.DataFrame([make_valid_row(Monthly_Expenditure=None)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_4_NULL"


def test_rule4_fail_null_department_id():
    df = pd.DataFrame([make_valid_row(Department_ID=None)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_4_NULL"
    assert "Department_ID" in result["rejected_rows"][0]["detail"]


def test_rule4_fail_null_monthly_expenditure():
    df = pd.DataFrame([make_valid_row(Monthly_Expenditure=None)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_4_NULL"
    assert "Monthly_Expenditure" in result["rejected_rows"][0]["detail"]


def test_rule4_fail_null_historical_average():
    df = pd.DataFrame([make_valid_row(Historical_Average_Expenditure=None)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_4_NULL"
    assert "Historical_Average_Expenditure" in result["rejected_rows"][0]["detail"]


def test_rule5_fail_date_month_mismatch():
    df = pd.DataFrame([make_valid_row(Transaction_Date="2023-02-15", Fiscal_Month=1)])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_5_DATE"


def test_multi_rule_failure_reports_first_rule_only():
    df = pd.DataFrame([make_valid_row(
        Budget_Utilization_Percentage=105.0,
        Transaction_Amount=-200,
    )])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 1
    assert len(result["rejected_rows"]) == 1
    assert result["rejected_rows"][0]["rule"] == "RULE_1_UTILIZATION"


def test_all_valid_rows():
    df = pd.DataFrame([
        make_valid_row(Transaction_ID=f"TXN00{i}")
        for i in range(1, 6)
    ])
    result = validate_dataframe(df)
    assert result["rejected_count"] == 0
    assert result["valid_count"] == 5
