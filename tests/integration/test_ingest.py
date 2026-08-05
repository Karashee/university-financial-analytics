"""Integration tests for POST /ingest/csv."""
import pandas as pd
import pytest

from app.core.security import hash_password
from app.models import Department, Role, User
from tests.conftest import TestingSessionLocal

CSV_COLUMNS = [
    "Transaction_ID", "Department_ID", "Department_Name", "Department_Type",
    "Fiscal_Year", "Fiscal_Month", "Transaction_Date", "Budget_Allocation",
    "Monthly_Expenditure", "Transaction_Amount", "Expenditure_Category",
    "Vendor_Category", "Budget_Utilization_Percentage", "Expenditure_Variance",
    "Historical_Average_Expenditure", "Expenditure_Growth_Rate",
    "Is_Anomaly", "Anomaly_Type",
]


def make_row(transaction_id: str, day: int = 1, transaction_amount: float = 1000.0) -> dict:
    return {
        "Transaction_ID": transaction_id,
        "Department_ID": "DEPT01",
        "Department_Name": "Finance and Administration",
        "Department_Type": "Administrative",
        "Fiscal_Year": 2023,
        "Fiscal_Month": 1,
        "Transaction_Date": f"2023-01-{day:02d}",
        "Budget_Allocation": 1000000,
        "Monthly_Expenditure": 50000.0,
        "Transaction_Amount": transaction_amount,
        "Expenditure_Category": "Administrative Operations",
        "Vendor_Category": "General Supplier",
        "Budget_Utilization_Percentage": 5.0,
        "Expenditure_Variance": 0.0,
        "Historical_Average_Expenditure": 50000.0,
        "Expenditure_Growth_Rate": 0.0,
        "Is_Anomaly": 0,
        "Anomaly_Type": "Normal",
    }


def build_csv_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture
def finance_token(client):
    db = TestingSessionLocal()
    try:
        role = Role(name="finance_officer", description="Finance Officer")
        db.add(role)
        db.commit()
        db.refresh(role)
        user = User(
            username="finance1",
            email="finance1@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
            department_id=None,
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/auth/token",
        data={"username": "finance1", "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def dept_head_token(client):
    db = TestingSessionLocal()
    try:
        role = Role(name="department_head", description="Department Head")
        db.add(role)
        db.commit()
        db.refresh(role)
        db.add(Department(
            department_id="DEPT01",
            department_name="Finance and Administration",
            department_type="Administrative",
        ))
        db.commit()
        user = User(
            username="depthead1",
            email="depthead1@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
            department_id="DEPT01",
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/auth/token",
        data={"username": "depthead1", "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_ingest_valid_csv_inserts_all_rows(client, finance_token):
    csv_bytes = build_csv_bytes([make_row(f"TXN00{i}", day=i) for i in range(1, 6)])
    response = client.post(
        "/ingest/csv",
        headers={"Authorization": f"Bearer {finance_token}"},
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid_rows"] == 5
    assert body["inserted_rows"] == 5
    assert body["skipped_rows"] == 0
    assert body["rejected_rows"] == []


def test_ingest_same_csv_twice_is_idempotent(client, finance_token):
    csv_bytes = build_csv_bytes([make_row(f"TXN00{i}", day=i) for i in range(1, 6)])

    first = client.post(
        "/ingest/csv",
        headers={"Authorization": f"Bearer {finance_token}"},
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert first.status_code == 200
    assert first.json()["inserted_rows"] == 5

    second = client.post(
        "/ingest/csv",
        headers={"Authorization": f"Bearer {finance_token}"},
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["inserted_rows"] == 0
    assert body["skipped_rows"] == 5


def test_ingest_rejects_row_with_invalid_amount(client, finance_token):
    rows = [make_row(f"TXN00{i}", day=i) for i in range(1, 5)]
    rows.append(make_row("TXN005", day=5, transaction_amount=-50))
    csv_bytes = build_csv_bytes(rows)

    response = client.post(
        "/ingest/csv",
        headers={"Authorization": f"Bearer {finance_token}"},
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inserted_rows"] == 4
    assert len(body["rejected_rows"]) == 1
    assert body["rejected_rows"][0]["rule"] == "RULE_2_AMOUNT"


def test_ingest_without_token_returns_401(client):
    csv_bytes = build_csv_bytes([make_row("TXN001")])
    response = client.post(
        "/ingest/csv",
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 401


def test_ingest_with_department_head_token_returns_403(client, dept_head_token):
    csv_bytes = build_csv_bytes([make_row("TXN001")])
    response = client.post(
        "/ingest/csv",
        headers={"Authorization": f"Bearer {dept_head_token}"},
        files={"file": ("transactions.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 403
