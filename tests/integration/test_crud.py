"""Integration tests for department, budget, and transaction CRUD endpoints."""
import pytest

from app.core.security import hash_password
from app.models import Department, Role, User
from tests.conftest import TestingSessionLocal


def _seed_role(name: str) -> int:
    db = TestingSessionLocal()
    try:
        role = Role(name=name, description=name)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role.id
    finally:
        db.close()


def _seed_user(username: str, role_id: int, department_id: str = None) -> None:
    db = TestingSessionLocal()
    try:
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=hash_password("password123"),
            role_id=role_id,
            department_id=department_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def _seed_department(department_id: str = "DEPT01", name: str = "Finance and Administration", type_: str = "Administrative") -> None:
    db = TestingSessionLocal()
    try:
        db.add(Department(department_id=department_id, department_name=name, department_type=type_))
        db.commit()
    finally:
        db.close()


def _get_token(client, username: str) -> str:
    response = client.post("/auth/token", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    role_id = _seed_role("admin")
    _seed_user("admin1", role_id)
    return _get_token(client, "admin1")


@pytest.fixture
def finance_token(client):
    role_id = _seed_role("finance_officer")
    _seed_user("finance1", role_id)
    return _get_token(client, "finance1")


@pytest.fixture
def dept_head_token(client):
    _seed_department("DEPT01")
    role_id = _seed_role("department_head")
    _seed_user("depthead1", role_id, department_id="DEPT01")
    return _get_token(client, "depthead1")


def make_transaction_payload(
    transaction_id: str,
    department_id: str = "DEPT01",
    transaction_amount: float = 1000.0,
    is_anomaly_ground_truth: int = 0,
    day: int = 1,
) -> dict:
    return {
        "transaction_id": transaction_id,
        "department_id": department_id,
        "fiscal_year": 2023,
        "fiscal_month": 1,
        "transaction_date": f"2023-01-{day:02d}",
        "transaction_amount": transaction_amount,
        "expenditure_category": "Administrative Operations",
        "vendor_category": "General Supplier",
        "monthly_expenditure": 50000.0,
        "budget_utilization_percentage": 5.0,
        "expenditure_variance": 0.0,
        "historical_average_expenditure": 50000.0,
        "expenditure_growth_rate": 0.0,
        "is_anomaly_ground_truth": is_anomaly_ground_truth,
        "anomaly_type_ground_truth": "Anomaly" if is_anomaly_ground_truth else "Normal",
    }


def test_create_department_success_then_duplicate_conflict(client, admin_token):
    payload = {
        "department_id": "DEPT01",
        "department_name": "Finance and Administration",
        "department_type": "Administrative",
    }
    first = client.post(
        "/departments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["department_id"] == "DEPT01"

    second = client.post(
        "/departments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert second.status_code == 409


def test_create_budget_success(client, admin_token):
    _seed_department("DEPT01")
    response = client.post(
        "/departments/DEPT01/budgets",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"department_id": "DEPT01", "fiscal_year": 2023, "budget_allocation": 1000000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department_id"] == "DEPT01"
    assert body["fiscal_year"] == 2023


def test_create_transaction_valid_row(client, finance_token):
    _seed_department("DEPT01")
    response = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {finance_token}"},
        json=make_transaction_payload("TXN001"),
    )
    assert response.status_code == 200
    assert response.json()["transaction_id"] == "TXN001"


def test_create_transaction_invalid_amount_returns_422(client, finance_token):
    _seed_department("DEPT01")
    response = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {finance_token}"},
        json=make_transaction_payload("TXN001", transaction_amount=-100),
    )
    assert response.status_code == 422


def test_get_transactions_filter_is_anomaly(client, finance_token):
    _seed_department("DEPT01")
    headers = {"Authorization": f"Bearer {finance_token}"}
    client.post("/transactions", headers=headers, json=make_transaction_payload("TXN001", is_anomaly_ground_truth=0, day=1))
    client.post("/transactions", headers=headers, json=make_transaction_payload("TXN002", is_anomaly_ground_truth=1, day=2))

    response = client.get("/transactions?is_anomaly=1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["transaction_id"] == "TXN002"


def test_get_transactions_department_head_sees_only_own_department(client, finance_token, dept_head_token):
    _seed_department("DEPT02", name="Academic Affairs", type_="Academic")
    headers = {"Authorization": f"Bearer {finance_token}"}
    client.post("/transactions", headers=headers, json=make_transaction_payload("TXN001", department_id="DEPT01", day=1))
    client.post("/transactions", headers=headers, json=make_transaction_payload("TXN002", department_id="DEPT02", day=2))

    response = client.get("/transactions", headers={"Authorization": f"Bearer {dept_head_token}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["department_id"] == "DEPT01"


def test_get_transactions_limit_exceeds_max_returns_422(client, finance_token):
    response = client.get("/transactions?limit=501", headers={"Authorization": f"Bearer {finance_token}"})
    assert response.status_code == 422


def test_get_transaction_not_found_returns_404(client, finance_token):
    response = client.get("/transactions/NONEXISTENT", headers={"Authorization": f"Bearer {finance_token}"})
    assert response.status_code == 404
