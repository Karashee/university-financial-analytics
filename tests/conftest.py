"""
Test configuration and fixtures.

Normal integration tests use SQLITE_TEST_DATABASE_URL (SQLite, no Alembic needed).
PostgreSQL view tests (Chunks 11, 14, 17) use TEST_DATABASE_URL and must be run
separately with a live PostgreSQL test database.
Do NOT mix SQLite and view tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.core.security import hash_password
from app.database import get_db
from app.main import app
from app.models import Base, Department, Role, User


# Create SQLite test engine
test_engine = create_engine(
    settings.sqlite_test_database_url,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """
    Set up test database before each test.
    Drop all tables and recreate them to ensure clean state.
    """
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Teardown: drop all tables after test
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Provide a TestClient for making requests to the FastAPI app."""
    return TestClient(app)


# Fixed test credentials, one user per role.
_SEEDED_CREDENTIALS = {
    "admin": ("admin_user", "password123"),
    "finance_officer": ("finance_user", "password123"),
    "department_head": ("depthead_user", "password123"),
}


@pytest.fixture
def seeded_client(client):
    """
    Provide (client, get_token) with one seeded user per role already in the
    SQLite test DB: admin and finance_officer with department_id=None,
    department_head with department_id="DEPT01". get_token(role_name) logs
    that role's user in via POST /auth/token and returns the access token.
    """
    db = TestingSessionLocal()
    try:
        roles = {}
        for role_name in ("admin", "finance_officer", "department_head"):
            role = Role(name=role_name, description=role_name)
            db.add(role)
            roles[role_name] = role
        db.commit()
        for role in roles.values():
            db.refresh(role)

        db.add(Department(
            department_id="DEPT01",
            department_name="Finance and Administration",
            department_type="Administrative",
        ))
        db.commit()

        for role_name, (username, password) in _SEEDED_CREDENTIALS.items():
            department_id = "DEPT01" if role_name == "department_head" else None
            db.add(User(
                username=username,
                email=f"{username}@example.com",
                hashed_password=hash_password(password),
                role_id=roles[role_name].id,
                department_id=department_id,
                is_active=True,
            ))
        db.commit()
    finally:
        db.close()

    def get_token(role_name: str) -> str:
        username, password = _SEEDED_CREDENTIALS[role_name]
        response = client.post("/auth/token", data={"username": username, "password": password})
        response.raise_for_status()
        return response.json()["access_token"]

    yield client, get_token
