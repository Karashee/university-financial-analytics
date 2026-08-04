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
from app.database import get_db
from app.main import app
from app.models import Base


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
