"""End-to-end integration test covering the full ingest -> analytics -> ML pipeline."""
import pandas as pd

CSV_COLUMNS = [
    "Transaction_ID", "Department_ID", "Department_Name", "Department_Type",
    "Fiscal_Year", "Fiscal_Month", "Transaction_Date", "Budget_Allocation",
    "Monthly_Expenditure", "Transaction_Amount", "Expenditure_Category",
    "Vendor_Category", "Budget_Utilization_Percentage", "Expenditure_Variance",
    "Historical_Average_Expenditure", "Expenditure_Growth_Rate",
    "Is_Anomaly", "Anomaly_Type",
]

DEPT_INFO = {
    "DEPT01": ("Finance and Administration", "Administrative"),
    "DEPT02": ("Academic Affairs", "Academic"),
}

BUDGETS = {
    ("DEPT01", 2022): 1_000_000.0,
    ("DEPT01", 2023): 1_200_000.0,
    ("DEPT02", 2022): 1_500_000.0,
    ("DEPT02", 2023): 1_700_000.0,
}


def make_row(
    transaction_id: str,
    department_id: str,
    fiscal_year: int,
    fiscal_month: int,
    day: int,
    vendor_category: str = "General Supplier",
) -> dict:
    department_name, department_type = DEPT_INFO[department_id]
    return {
        "Transaction_ID": transaction_id,
        "Department_ID": department_id,
        "Department_Name": department_name,
        "Department_Type": department_type,
        "Fiscal_Year": fiscal_year,
        "Fiscal_Month": fiscal_month,
        "Transaction_Date": f"{fiscal_year}-{fiscal_month:02d}-{day:02d}",
        "Budget_Allocation": BUDGETS[(department_id, fiscal_year)],
        "Monthly_Expenditure": 50_000.0,
        "Transaction_Amount": 10_000.0,
        "Expenditure_Category": "Administrative Operations",
        "Vendor_Category": vendor_category,
        "Budget_Utilization_Percentage": 20.0,
        "Expenditure_Variance": 2_000.0,
        "Historical_Average_Expenditure": 48_000.0,
        "Expenditure_Growth_Rate": 0.02,
        "Is_Anomaly": 0,
        "Anomaly_Type": "Normal",
    }


def build_rows() -> list[dict]:
    """2 departments x 3 months x 2 fiscal years (12 rows) + 3 extra rows = 15 rows total."""
    rows = []
    counter = 1
    for dept in DEPT_INFO:
        for year in (2022, 2023):
            for month in (1, 2, 3):
                rows.append(make_row(f"TXN{counter:03d}", dept, year, month, day=1))
                counter += 1

    # 3 extra rows: a second transaction in 3 of the dept-year-months above.
    for dept, year, month in [("DEPT01", 2023, 1), ("DEPT02", 2023, 2), ("DEPT01", 2022, 3)]:
        rows.append(make_row(f"TXN{counter:03d}", dept, year, month, day=15, vendor_category="Regulatory Body"))
        counter += 1

    return rows


def build_csv_bytes() -> bytes:
    df = pd.DataFrame(build_rows(), columns=CSV_COLUMNS)
    return df.to_csv(index=False).encode("utf-8")


def test_full_pipeline(seeded_client):
    client, get_token = seeded_client
    finance_headers = {"Authorization": f"Bearer {get_token('finance_officer')}"}
    dept_head_headers = {"Authorization": f"Bearer {get_token('department_head')}"}

    # Step 1: ingest
    ingest_response = client.post(
        "/ingest/csv",
        headers=finance_headers,
        files={"file": ("transactions.csv", build_csv_bytes(), "text/csv")},
    )
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()
    assert ingest_body["inserted_rows"] > 0

    # Step 2: budget utilization
    budget_util_response = client.post("/analytics/compute/budget-utilization", headers=finance_headers)
    assert budget_util_response.status_code == 200
    assert budget_util_response.json()["rows_written"] > 0

    # Step 3: trend summaries
    trend_response = client.post("/reporting/compute/trend-summaries", headers=finance_headers)
    assert trend_response.status_code == 200
    assert trend_response.json()["rows_written"] > 0

    # Step 4: anomaly detection
    anomaly_response = client.post("/anomaly/detect", headers=finance_headers)
    assert anomaly_response.status_code == 200
    anomaly_body = anomaly_response.json()
    assert anomaly_body["total_scored"] == ingest_body["inserted_rows"]
    assert anomaly_body["model_version"] == "IF_v1.0"

    # Step 5: expenditure forecast
    forecast_response = client.post("/forecasts/run?n_months=3", headers=finance_headers)
    assert forecast_response.status_code == 200
    forecast_body = forecast_response.json()
    assert forecast_body["total_forecasts"] > 0
    assert forecast_body["mae_context"] >= 0

    # Step 6: dept_head-scoped budget utilization read
    dept_budget_response = client.get("/analytics/budget-utilization", headers=dept_head_headers)
    assert dept_budget_response.status_code == 200
    dept_budget_body = dept_budget_response.json()
    assert len(dept_budget_body) > 0
    assert all(row["department_id"] == "DEPT01" for row in dept_budget_body)

    # Step 7: dept_head-scoped anomaly results read
    dept_anomaly_response = client.get("/anomaly/results", headers=dept_head_headers)
    assert dept_anomaly_response.status_code == 200
    dept_anomaly_body = dept_anomaly_response.json()
    assert len(dept_anomaly_body) > 0
    assert all(row["department_id"] == "DEPT01" for row in dept_anomaly_body)

    # Step 8: dept_head-scoped forecast read
    dept_forecast_response = client.get("/forecasts", headers=dept_head_headers)
    assert dept_forecast_response.status_code == 200
    dept_forecast_body = dept_forecast_response.json()
    assert len(dept_forecast_body) > 0
    assert all(row["department_id"] == "DEPT01" for row in dept_forecast_body)
    assert all(row["predicted_expenditure"] >= 0 for row in dept_forecast_body)
