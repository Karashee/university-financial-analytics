"""
Idempotent local-development seed script.

Seeds the 3 roles, ingests a CSV of expenditure transactions (through the
running API, using a bootstrap admin user), creates the 3 standard local-dev
users, and computes the derived analytics/reporting tables. Running this
script twice produces the same end state.
"""
import argparse

import httpx
from sqlalchemy import create_engine, text

from app.config import settings
from app.core.security import hash_password

# FOR LOCAL DEVELOPMENT ONLY - CHANGE IN PRODUCTION
ADMIN_USERNAME, ADMIN_PASSWORD = "admin", "Admin@123"
FINANCE_USERNAME, FINANCE_PASSWORD = "finance", "Finance@123"
DEPTHEAD_USERNAME, DEPTHEAD_PASSWORD = "depthead", "DeptHead@123"

ROLE_DESCRIPTIONS = {
    "admin": "Full system access",
    "finance_officer": "Finance operations access",
    "department_head": "Department-scoped access",
}


def seed_roles(engine) -> None:
    """INSERT roles ON CONFLICT (name) DO NOTHING."""
    with engine.begin() as conn:
        for role_name, description in ROLE_DESCRIPTIONS.items():
            conn.execute(
                text(
                    "INSERT INTO roles (name, description) VALUES (:name, :description) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"name": role_name, "description": description},
            )


def ensure_bootstrap_admin(engine) -> None:
    """
    Insert the admin user directly (with a hash of its final password) if it
    doesn't exist yet, so there are credentials to call POST /ingest/csv
    before any user has been created through the API.
    """
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM users WHERE username = :username"),
            {"username": ADMIN_USERNAME},
        ).first()
        if existing is not None:
            return

        conn.execute(
            text(
                "INSERT INTO users (username, email, hashed_password, role_id, "
                "department_id, is_active) "
                "SELECT :username, :email, :hashed_password, r.id, NULL, true "
                "FROM roles r WHERE r.name = 'admin'"
            ),
            {
                "username": ADMIN_USERNAME,
                "email": "admin@example.edu",
                "hashed_password": hash_password(ADMIN_PASSWORD),
            },
        )


def get_admin_token(server_url: str) -> str:
    response = httpx.post(
        f"{server_url}/auth/token",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def ingest_csv(server_url: str, csv_path: str, token: str) -> dict:
    with open(csv_path, "rb") as csv_file:
        response = httpx.post(
            f"{server_url}/ingest/csv",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (csv_path, csv_file, "text/csv")},
            timeout=60.0,
        )
    response.raise_for_status()
    return response.json()


def get_first_department_id(engine) -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT department_id FROM departments ORDER BY department_id LIMIT 1")
        ).first()
    if row is None:
        raise RuntimeError("No departments found - CSV ingestion must run before seeding users.")
    return row[0]


def seed_users(engine, dept_head_department_id: str) -> None:
    """INSERT users ON CONFLICT (username) DO NOTHING."""
    users = [
        (ADMIN_USERNAME, "admin@example.edu", ADMIN_PASSWORD, "admin", None),
        (FINANCE_USERNAME, "finance@example.edu", FINANCE_PASSWORD, "finance_officer", None),
        (DEPTHEAD_USERNAME, "depthead@example.edu", DEPTHEAD_PASSWORD, "department_head", dept_head_department_id),
    ]
    with engine.begin() as conn:
        for username, email, password, role_name, department_id in users:
            conn.execute(
                text(
                    "INSERT INTO users (username, email, hashed_password, role_id, "
                    "department_id, is_active) "
                    "SELECT :username, :email, :hashed_password, r.id, :department_id, true "
                    "FROM roles r WHERE r.name = :role_name "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {
                    "username": username,
                    "email": email,
                    "hashed_password": hash_password(password),
                    "role_name": role_name,
                    "department_id": department_id,
                },
            )


def compute_analytics(server_url: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    httpx.post(
        f"{server_url}/analytics/compute/budget-utilization", headers=headers, timeout=60.0
    ).raise_for_status()
    httpx.post(
        f"{server_url}/reporting/compute/trend-summaries", headers=headers, timeout=60.0
    ).raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotent local-development seed script.")
    parser.add_argument("--csv", required=True, help="Path to the expenditure transactions CSV file.")
    parser.add_argument("--server-url", default="http://localhost:8000", help="Base URL of the running API server.")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)

    seed_roles(engine)
    ensure_bootstrap_admin(engine)

    admin_token = get_admin_token(args.server_url)

    ingest_result = ingest_csv(args.server_url, args.csv, admin_token)
    print(f"Ingestion result: {ingest_result}")

    dept_head_department_id = get_first_department_id(engine)
    seed_users(engine, dept_head_department_id)

    compute_analytics(args.server_url, admin_token)

    print(
        f"=== Seed complete: {ingest_result['inserted_rows']} transactions, "
        f"dept_head assigned to {dept_head_department_id} ==="
    )


if __name__ == "__main__":
    main()
