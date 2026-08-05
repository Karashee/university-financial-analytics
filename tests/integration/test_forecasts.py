"""Integration tests for the Linear Regression expenditure forecast endpoints."""
from datetime import date
 
import pytest
 
from app.core.security import hash_password
from app.models import Budget, Department, ExpenditureTransaction, Role, User
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
 
 
def _seed_department(department_id: str, name: str) -> None:
    db = TestingSessionLocal()
    try:
        db.add(Department(department_id=department_id, department_name=name, department_type="Administrative"))
        db.commit()
    finally:
        db.close()
 
 
def _seed_budget(department_id: str, fiscal_year: int, budget_allocation: float) -> None:
    db = TestingSessionLocal()
    try:
        db.add(Budget(department_id=department_id, fiscal_year=fiscal_year, budget_allocation=budget_allocation))
        db.commit()
    finally:
        db.close()
 
 
def _seed_transaction(
    transaction_id: str,
    department_id: str,
    fiscal_month: int,
    monthly_expenditure: float,
) -> None:
    db = TestingSessionLocal()
    try:
        db.add(ExpenditureTransaction(
            transaction_id=transaction_id,
            department_id=department_id,
            fiscal_year=2023,
            fiscal_month=fiscal_month,
            transaction_date=date(2023, fiscal_month, 1),
            monthly_expenditure=monthly_expenditure,
            transaction_amount=monthly_expenditure * 0.5,
            expenditure_category="Administrative Operations",
            vendor_category="General Supplier",
            budget_utilization_percentage=20.0,
            expenditure_variance=0.0,
            historical_average_expenditure=monthly_expenditure * 0.9,
            expenditure_growth_rate=0.02,
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
def seeded_forecast_data():
    _seed_department("DEPT01", "Finance and Administration")
    _seed_department("DEPT02", "Academic Affairs")
    _seed_budget("DEPT01", 2023, 2_000_000.0)
    _seed_budget("DEPT02", 2023, 3_000_000.0)
 
    for month in range(1, 13):
        _seed_transaction(f"D1-{month:02d}", "DEPT01", month, 100_000.0 + month * 1_000.0)
    for month in range(1, 13):
        _seed_transaction(f"D2-{month:02d}", "DEPT02", month, 200_000.0 + month * 1_500.0)
 
 
def test_run_forecast_returns_expected_totals(client, finance_token, seeded_forecast_data):
    response = client.post(
        "/forecasts/run?n_months=3",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_forecasts"] == 6
    assert body["mae_context"] >= 0
    assert body["model_version"] == "LR_v1.0"
    assert body["n_months_ahead"] == 3
 
 
def test_run_forecast_n_months_out_of_range_returns_422(client, finance_token, seeded_forecast_data):
    headers = {"Authorization": f"Bearer {finance_token}"}
    too_low = client.post("/forecasts/run?n_months=0", headers=headers)
    assert too_low.status_code == 422
 
    too_high = client.post("/forecasts/run?n_months=13", headers=headers)
    assert too_high.status_code == 422
 
 
def test_get_forecasts_all_predictions_non_negative(client, finance_token, seeded_forecast_data):
    headers = {"Authorization": f"Bearer {finance_token}"}
    client.post("/forecasts/run?n_months=3", headers=headers)
 
    response = client.get("/forecasts", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(row["predicted_expenditure"] >= 0 for row in body)
 
 
def test_get_forecasts_filter_by_department(client, finance_token, seeded_forecast_data):
    headers = {"Authorization": f"Bearer {finance_token}"}
    client.post("/forecasts/run?n_months=3", headers=headers)
 
    response = client.get("/forecasts?department_id=DEPT01", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(row["department_id"] == "DEPT01" for row in body)
 
 
def test_forecast_chains_lag_across_months(client, finance_token, seeded_forecast_data, monkeypatch):
    """
    Guards against the single-shot regression: prepare_future_months must be
    called once PER forecasted month, with each department's lag anchor
    updated from the prior step's own prediction - not called once with the
    full n_months, which silently freezes lag_1_expenditure at the last
    actual value for every month after the first.
    """
    import app.services.forecast_service as forecast_service_module
 
    original_prepare = forecast_service_module.prepare_future_months
    seen_lag_snapshots = []
 
    def spy_prepare_future_months(unique_depts, dept_last_month, *args, **kwargs):
        seen_lag_snapshots.append({dept: dept_last_month[dept][2] for dept in unique_depts})
        return original_prepare(unique_depts, dept_last_month, *args, **kwargs)
 
    monkeypatch.setattr(forecast_service_module, "prepare_future_months", spy_prepare_future_months)
 
    response = client.post(
        "/forecasts/run?n_months=3",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert response.status_code == 200
 
    # Called once per forecasted month, not once for the whole batch.
    assert len(seen_lag_snapshots) == 3
 
    # If chaining works, each department's lag anchor changes between calls -
    # fed from the prior step's own prediction, not frozen at the last actual.
    for dept in ("DEPT01", "DEPT02"):
        assert seen_lag_snapshots[0][dept] != seen_lag_snapshots[1][dept]
        assert seen_lag_snapshots[1][dept] != seen_lag_snapshots[2][dept]
 
 
def test_dept_head_sees_only_own_department(
    client, finance_token, dept_head_token_dept01, seeded_forecast_data
):
    run = client.post(
        "/forecasts/run?n_months=3",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert run.status_code == 200
    assert run.json()["total_forecasts"] == 6
 
    response = client.get(
        "/forecasts",
        headers={"Authorization": f"Bearer {dept_head_token_dept01}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert all(row["department_id"] == "DEPT01" for row in body)
 