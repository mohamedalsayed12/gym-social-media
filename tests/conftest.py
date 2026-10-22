import os

import app.models  # noqa: F401
import pytest
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.database import build_database_url, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def build_test_database_url():
    explicit_url = os.getenv("TEST_DATABASE_URL")
    url = make_url(explicit_url) if explicit_url else build_database_url(settings)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg2")
    if not explicit_url and url.database:
        url = url.set(database=f"{url.database}_test")
    if not url.database or not url.database.endswith("_test"):
        raise ValueError("Test database name must end with '_test'")
    return url


engine = create_engine(build_test_database_url())
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def session():
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user(client):
    user_data = {
        "email": "mohamedalsayed@gmail.com",
        "username": "mohamed",
        "password": "password123",
        "bodyweight_kg": 70,
        "height_cm": 180,
    }
    res = client.post("/users/", json=user_data)
    assert res.status_code == 201
    new_user = res.json()
    new_user["password"] = user_data["password"]
    return new_user


@pytest.fixture
def test_user2(client):
    user_data = {
        "email": "nora@example.com",
        "username": "nora",
        "password": "password123",
        "bodyweight_kg": 60,
        "height_cm": 170,
    }
    res = client.post("/users/", json=user_data)
    assert res.status_code == 201
    new_user = res.json()
    new_user["password"] = user_data["password"]
    return new_user


@pytest.fixture
def token(test_user):
    return create_access_token(test_user["id"])


@pytest.fixture
def authorized_client(client, token):
    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return client
