"""Shared test fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _auth_headers(client, email, name="User"):
    resp = client.post("/signup", json={"email": email, "name": name, "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def alice_headers(client):
    return _auth_headers(client, "alice@example.com", "Alice")


@pytest.fixture()
def bob_headers(client):
    return _auth_headers(client, "bob@example.com", "Bob")


@pytest.fixture()
def workspace(client, alice_headers):
    resp = client.post("/workspaces", json={"name": "Engineering", "key": "ENG"}, headers=alice_headers)
    return resp.json()
