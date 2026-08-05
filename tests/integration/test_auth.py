"""Integration tests for authentication and role-based access."""


def test_login_with_correct_credentials_returns_token(seeded_client):
    client, _ = seeded_client
    response = client.post(
        "/auth/token",
        data={"username": "admin_user", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.post(
        "/auth/token",
        data={"username": "admin_user", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_with_nonexistent_username_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.post(
        "/auth/token",
        data={"username": "no_such_user", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_users_with_admin_token_returns_200(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {get_token('admin')}"},
    )
    assert response.status_code == 200


def test_get_users_with_finance_officer_token_returns_403(seeded_client):
    client, get_token = seeded_client
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {get_token('finance_officer')}"},
    )
    assert response.status_code == 403


def test_get_users_without_authorization_header_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.get("/users")
    assert response.status_code == 401


def test_get_users_with_invalid_jwt_returns_401(seeded_client):
    client, _ = seeded_client
    response = client.get(
        "/users",
        headers={"Authorization": "Bearer notavalidjwt"},
    )
    assert response.status_code == 401
