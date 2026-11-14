"""Integration tests for GET /auth/me and GET /logs."""
from datetime import datetime, timedelta, timezone

from app.models import SystemLog
from tests.conftest import TestingSessionLocal

# Oldest first, so the newest message is the last one seeded.
_SEEDED_LOGS = [
    ("INFO", "oldest entry"),
    ("WARNING", "middle entry"),
    ("ERROR", "newest entry"),
]


def _seed_logs() -> None:
    """Insert three log rows one minute apart, oldest first."""
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    try:
        for offset, (level, message) in enumerate(_SEEDED_LOGS):
            db.add(SystemLog(
                logged_at=base + timedelta(minutes=offset),
                level=level,
                logger_name="app.services.seeded",
                message=message,
                module="test_logs_and_me",
                function_name="_seed_logs",
                line_number=offset + 1,
            ))
        db.commit()
    finally:
        db.close()


# --- GET /auth/me ---

def test_me_returns_admin_role(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {get_token('admin')}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin_user"
    assert body["role"] == "admin"
    assert body["department_id"] is None
    assert body["department_name"] is None


def test_me_returns_finance_officer_role(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "finance_user"
    assert body["role"] == "finance_officer"
    assert body["department_id"] is None
    assert body["department_name"] is None


def test_me_returns_department_head_with_department(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {get_token('department_head')}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "depthead_user"
    assert body["role"] == "department_head"
    assert body["department_id"] == "DEPT01"
    assert body["department_name"] == "Finance and Administration"


def test_me_without_token_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.get("/auth/me")
    assert response.status_code == 401


# --- GET /logs ---

def test_logs_returns_200_for_finance_officer(seeded_client):
    client, get_token = seeded_client
    _seed_logs()
    response = client.get(
        "/logs",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(_SEEDED_LOGS)
    assert set(body[0].keys()) == {"id", "logged_at", "level", "logger_name", "message"}


def test_logs_returns_403_for_department_head(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/logs",
        headers={"Authorization": f"Bearer {get_token('department_head')}"},
    )
    assert response.status_code == 403


def test_logs_without_token_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.get("/logs")
    assert response.status_code == 401


def test_logs_limit_above_maximum_returns_422(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/logs?limit=201",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 422


def test_logs_limit_below_minimum_returns_422(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/logs?limit=0",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 422


def test_logs_returns_newest_first(seeded_client):
    client, get_token = seeded_client
    _seed_logs()
    response = client.get(
        "/logs",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 200
    messages = [row["message"] for row in response.json()]
    assert messages == [message for _, message in reversed(_SEEDED_LOGS)]


def test_logs_level_filter_returns_only_that_level(seeded_client):
    client, get_token = seeded_client
    _seed_logs()
    response = client.get(
        "/logs?level=ERROR",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["level"] == "ERROR"
    assert body[0]["message"] == "newest entry"


def test_logs_limit_caps_number_of_rows(seeded_client):
    client, get_token = seeded_client
    _seed_logs()
    response = client.get(
        "/logs?limit=2",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
