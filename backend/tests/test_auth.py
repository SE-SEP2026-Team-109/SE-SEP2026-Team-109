def test_register_creates_user(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "student@study.iitm.ac.in", "password": "password123", "role": "student"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "student@study.iitm.ac.in"
    assert body["role"] == "student"
    assert "password" not in body


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@study.iitm.ac.in", "password": "password123", "role": "student"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400


def test_login_returns_token_for_valid_credentials(client):
    client.post(
        "/api/auth/register",
        json={"email": "mentor@mentorconnect.in", "password": "password123", "role": "mentor"},
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "mentor@mentorconnect.in", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrongpw@study.iitm.ac.in", "password": "password123", "role": "student"},
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "wrongpw@study.iitm.ac.in", "password": "nope"},
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "me@study.iitm.ac.in", "password": "password123", "role": "student"},
    )
    assert register.status_code == 201

    login = client.post(
        "/api/auth/login",
        data={"username": "me@study.iitm.ac.in", "password": "password123"},
    )
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@study.iitm.ac.in"


def test_me_rejects_missing_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
