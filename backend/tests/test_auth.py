def test_signup_returns_token(client):
    resp = client.post("/signup", json={"email": "new@example.com", "name": "New", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_succeeds_with_correct_password(client):
    client.post("/signup", json={"email": "u@example.com", "name": "U", "password": "password123"})
    resp = client.post("/login", json={"email": "u@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_fails_with_wrong_password(client):
    client.post("/signup", json={"email": "u2@example.com", "name": "U2", "password": "password123"})
    resp = client.post("/login", json={"email": "u2@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/me").status_code == 401


def test_me_returns_current_user(client, alice_headers):
    resp = client.get("/me", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_duplicate_email_rejected(client):
    client.post("/signup", json={"email": "dup@example.com", "name": "D", "password": "password123"})
    resp = client.post("/signup", json={"email": "dup@example.com", "name": "D2", "password": "password123"})
    assert resp.status_code == 400
