"""Integration tests for the Isolation Forest anomaly detection endpoints."""
from datetime import date
 
import pytest
 
from app.core.security import hash_password
from app.models import AnomalyResult, Department, ExpenditureTransaction, Role, User
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
 
 
def _seed_user(username: str, role_id: int, department_id: str | None = None) -> None:
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
 
 
def _seed_department(department_id: str = "DEPT01") -> None:
    db = TestingSessionLocal()
    try:
        db.add(Department(
            department_id=department_id,
            department_name="Finance and Administration",
            department_type="Administrative",
        ))
        db.commit()
    finally:
        db.close()
 
 
def _seed_transaction(
    transaction_id: str,
    transaction_amount: float,
    day: int,
    department_id: str = "DEPT01",
) -> None:
    db = TestingSessionLocal()
    try:
        db.add(ExpenditureTransaction(
            transaction_id=transaction_id,
            department_id=department_id,
            fiscal_year=2023,
            fiscal_month=1,
            transaction_date=date(2023, 1, day),
            monthly_expenditure=500000.0,
            transaction_amount=transaction_amount,
            expenditure_category="Administrative Operations",
            vendor_category="General Supplier",
            budget_utilization_percentage=20.0,
            expenditure_variance=0.0,
            historical_average_expenditure=100000.0,
            expenditure_growth_rate=0.0,
        ))
        db.commit()
    finally:
        db.close()
 
 
def _get_token(client, username: str) -> str:
    response = client.post("/auth/token", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]
 
 
@pytest.fixture
def finance_token(client):
    role_id = _seed_role("finance_officer")
    _seed_user("finance1", role_id)
    return _get_token(client, "finance1")
 
 
@pytest.fixture
def dept_head_token_dept01(client):
    role_id = _seed_role("department_head")
    _seed_user("depthead1", role_id, department_id="DEPT01")
    return _get_token(client, "depthead1")
 
 
@pytest.fixture
def seeded_transactions():
    _seed_department("DEPT01")
    # 17 normal transactions
    for i in range(1, 18):
        _seed_transaction(f"TXN{i:03d}", transaction_amount=50_000.0 + i * 100, day=i)
    # 3 outliers, roughly 50x+ the baseline amount - kept distinct from each other
    # (not exact duplicates) so IsolationForest's percentile threshold doesn't land
    # on a tied score, which would leave all of them un-flagged.
    for offset, i in enumerate(range(18, 21)):
        _seed_transaction(f"TXN{i:03d}", transaction_amount=(58 + offset) * 50_000.0, day=i)
 
 
@pytest.fixture
def seeded_two_department_transactions():
    """5 transactions under DEPT01, 5 under DEPT02 - for dept_head isolation testing.
    Amounts are unremarkable on purpose; this fixture tests filtering of results
    (flagged + normal both get stored per Chunk 14 spec), not detection accuracy."""
    _seed_department("DEPT01")
    _seed_department("DEPT02")
    for i in range(1, 6):
        _seed_transaction(f"D1TXN{i:02d}", transaction_amount=50_000.0 + i * 100, day=i, department_id="DEPT01")
    for i in range(1, 6):
        _seed_transaction(f"D2TXN{i:02d}", transaction_amount=60_000.0 + i * 100, day=i, department_id="DEPT02")
 
 
def test_detect_anomalies_scores_all_transactions(client, finance_token, seeded_transactions):
    response = client.post("/anomaly/detect", headers={"Authorization": f"Bearer {finance_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_scored"] == 20
    assert body["flagged_count"] >= 0
    assert body["model_version"] == "IF_v1.0"
 
 
def test_get_anomaly_results_returns_list(client, finance_token, seeded_transactions):
    client.post("/anomaly/detect", headers={"Authorization": f"Bearer {finance_token}"})
    response = client.get("/anomaly/results", headers={"Authorization": f"Bearer {finance_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
 
 
def test_get_anomaly_results_filter_is_anomaly_predicted(client, finance_token, seeded_transactions):
    client.post("/anomaly/detect", headers={"Authorization": f"Bearer {finance_token}"})
    response = client.get(
        "/anomaly/results?is_anomaly_predicted=true",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(row["is_anomaly_predicted"] is True for row in body)
 
 
def test_rerun_detection_does_not_duplicate_results(client, finance_token, seeded_transactions):
    headers = {"Authorization": f"Bearer {finance_token}"}
 
    first = client.post("/anomaly/detect", headers=headers)
    assert first.status_code == 200
 
    db = TestingSessionLocal()
    try:
        count_after_first = db.query(AnomalyResult).count()
    finally:
        db.close()
 
    second = client.post("/anomaly/detect", headers=headers)
    assert second.status_code == 200
 
    db = TestingSessionLocal()
    try:
        count_after_second = db.query(AnomalyResult).count()
    finally:
        db.close()
 
    assert count_after_first == 20
    assert count_after_second == 20
 
 
def test_dept_head_sees_only_own_department(
    client, finance_token, dept_head_token_dept01, seeded_two_department_transactions
):
    detect = client.post("/anomaly/detect", headers={"Authorization": f"Bearer {finance_token}"})
    assert detect.status_code == 200
    assert detect.json()["total_scored"] == 10
 
    response = client.get(
        "/anomaly/results",
        headers={"Authorization": f"Bearer {dept_head_token_dept01}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert all(row["department_id"] == "DEPT01" for row in body)
 