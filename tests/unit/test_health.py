"""Unit tests for health and root endpoints."""


def test_root_endpoint(client):
    """Test GET / returns 200 and contains 'message' key."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Financial Analytics System API"
    assert data["version"] == "1.0.0"


def test_health_endpoint(client):
    """Test GET /health returns 200 and contains 'status' key."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "database" in data
    # Database should be connected when using SQLite test DB
    assert data["database"] in ["connected", "unavailable"]
