
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


def test_forgot_password_registered_email(client):
    register_user(client, email="forgot@example.com")

    response = client.post(
        "/auth/forgot-password",
        json={"email": "forgot@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["reset_token"] is not None


def test_forgot_password_unregistered_email(client):
    response = client.post(
        "/auth/forgot-password",
        json={"email": "notfound@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["reset_token"] is None


def test_reset_password_flow(client):
    register_user(client, email="reset@example.com")

    forgot_res = client.post(
        "/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    token = forgot_res.json()["reset_token"]

    reset_res = client.post(
        "/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewSecretPassword123",
        },
    )
    assert reset_res.status_code == 200

    # Old password must no longer work
    old_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "TestPassword123"},
    )
    assert old_login.status_code == 401

    # New password must work
    new_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "NewSecretPassword123"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_reset_password_cannot_reuse_token(client):
    register_user(client, email="reuse@example.com")

    forgot_res = client.post(
        "/auth/forgot-password",
        json={"email": "reuse@example.com"},
    )
    token = forgot_res.json()["reset_token"]

    first_reset = client.post(
        "/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewPasswordOne123",
        },
    )
    assert first_reset.status_code == 200

    # Reusing the exact same token must fail
    second_reset = client.post(
        "/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewPasswordTwo123",
        },
    )
    assert second_reset.status_code == 400


def test_reset_password_invalid_token(client):
    response = client.post(
        "/auth/reset-password",
        json={
            "token": "invalid.jwt.token",
            "new_password": "ValidPassword123",
        },
    )
    assert response.status_code == 400


def test_reset_password_short_password(client):
    response = client.post(
        "/auth/reset-password",
        json={
            "token": "some-token",
            "new_password": "123",
        },
    )
    assert response.status_code == 422


def test_rate_limiter_blocks_excessive_requests(client):
    import app.rate_limiter
    from app.routers.auth import forgot_rate_limiter

    app.rate_limiter.RATE_LIMIT_ENABLED = True
    forgot_rate_limiter.requests.clear()

    try:
        # forgot-password has limit of 3 requests per 600s
        for _ in range(3):
            client.post(
                "/auth/forgot-password",
                json={"email": "rate@example.com"},
            )

        # 4th request must be rate limited with 429
        blocked_response = client.post(
            "/auth/forgot-password",
            json={"email": "rate@example.com"},
        )
        assert blocked_response.status_code == 429
        assert "Retry-After" in blocked_response.headers
        assert "Too many requests" in blocked_response.json()["detail"]
    finally:
        app.rate_limiter.RATE_LIMIT_ENABLED = False



def test_email_service_graceful_mock():
    from app.email_service import send_password_reset_email

    # When SMTP is not configured, it should return False without raising an exception
    result = send_password_reset_email("test@example.com", "dummy_token_123")
    assert result is False


