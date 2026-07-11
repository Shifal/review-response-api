import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app import models


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure tables exist before any test runs, and clean up test data after the full session."""
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up: remove all data created during this test session
    db = SessionLocal()
    try:
        db.query(models.PropertyScore).delete()
        db.query(models.ReviewResponse).delete()
        db.query(models.Review).delete()
        db.query(models.Property).delete()
        db.query(models.User).delete()
        db.query(models.Company).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Signs up a fresh test company/user and returns ready-to-use auth headers."""
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    response = client.post("/auth/signup", json={
        "company_name": "Test Company",
        "email": unique_email,
        "password": "TestPass123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_property(client, auth_headers):
    response = client.post("/properties", json={
        "name": "Test Property",
        "city": "Test City",
    }, headers=auth_headers)
    return response.json()