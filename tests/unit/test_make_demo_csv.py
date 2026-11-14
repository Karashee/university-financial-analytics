import pandas as pd

from scripts.make_demo_csv import build_demo_rows
from scripts.validate_csv import validate_dataframe


def make_valid_row(**overrides) -> dict:
    row = {
        "Transaction_ID": "TXN001",
        "Department_ID": "DEPT01",
        "Department_Name": "Finance and Administration",
        "Department_Type": "Administrative",
        "Fiscal_Year": 2023,
        "Fiscal_Month": 1,
        "Transaction_Date": "2023-01-15",
        "Budget_Allocation": 15500000,
        "Monthly_Expenditure": 100000.0,
        "Transaction_Amount": 5000.0,
        "Expenditure_Category": "Administrative Operations",
        "Vendor_Category": "General Supplier",
        "Budget_Utilization_Percentage": 65.0,
        "Expenditure_Variance": 5000.0,
        "Historical_Average_Expenditure": 95000.0,
        "Expenditure_Growth_Rate": 0.0,
        "Is_Anomaly": 0,
        "Anomaly_Type": "Normal",
    }
    row.update(overrides)
    return row


def test_build_demo_rows_returns_three_rows():
    df = pd.DataFrame([make_valid_row()])
    demo_rows = build_demo_rows(df)
    assert len(demo_rows) == 3


def test_build_demo_rows_have_unique_demo_transaction_ids():
    df = pd.DataFrame([make_valid_row()])
    demo_rows = build_demo_rows(df)
    ids = [row["Transaction_ID"] for row in demo_rows]
    assert ids == ["DEMO001", "DEMO002", "DEMO003"]


def test_build_demo_rows_rejected_with_expected_rules_in_order():
    df = pd.DataFrame([make_valid_row()])
    demo_rows = build_demo_rows(df)
    demo_df = pd.DataFrame(demo_rows)

    result = validate_dataframe(demo_df)

    assert result["rejected_count"] == 3
    rules = [entry["rule"] for entry in result["rejected_rows"]]
    assert rules == ["RULE_1_UTILIZATION", "RULE_2_AMOUNT", "RULE_5_DATE"]


def test_build_demo_rows_date_defect_keeps_same_year():
    df = pd.DataFrame([make_valid_row(Fiscal_Year=2023, Fiscal_Month=1)])
    demo_rows = build_demo_rows(df)
    date_defect = demo_rows[2]
    assert date_defect["Transaction_Date"].startswith("2023-")
    assert date_defect["Transaction_Date"] != "2023-01-10"


def test_build_demo_rows_december_wraps_to_november_not_next_year():
    df = pd.DataFrame([make_valid_row(Fiscal_Year=2023, Fiscal_Month=12, Transaction_Date="2023-12-15")])
    demo_rows = build_demo_rows(df)
    date_defect = demo_rows[2]
    assert date_defect["Transaction_Date"] == "2023-11-10"
