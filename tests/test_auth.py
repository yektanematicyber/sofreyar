
def register_user(client, email="test@example.com"):
    return client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "TestPassword123",
        },
    )


def login_user(client, email="test@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )


def test_register_success(client):
    response = register_user(client)

    assert response.status_code == 201
    assert response.json()["name"] == "Test User"
    assert response.json()["email"] == "test@example.com"
    assert "hashed_password" not in response.json()


def test_register_duplicate_email(client):
    register_user(client)

    response = register_user(client)

    assert response.status_code == 409


def test_register_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "invalid-email",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 422


def test_register_short_password(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "short@example.com",
            "password": "123",
        },
    )

    assert response.status_code == 422


def test_login_success(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_get_current_user(client):
    register_user(client)

    login_response = login_user(client)
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
    assert response.json()["email"] == "test@example.com"


def test_get_current_user_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
