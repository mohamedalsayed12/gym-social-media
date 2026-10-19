from fastapi.testclient import TestClient
from main import app
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from config import settings
from database import Base, build_database_url, get_db
import pytest
from oauth2 import create_access_token
import models
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
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture()
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user(client):
    user_data = {"email": "user@example.com", "password": "password123"}
    res = client.post("/users/", json=user_data)
    assert res.status_code==201
    new_user = res.json()
    new_user["password"] = user_data["password"]
    return new_user


@pytest.fixture
def test_user2(client):
    user_data = {"email": "nora@example.com", "password": "password123"}
    res = client.post("/users/", json=user_data)
    assert res.status_code == 201
    new_user = res.json()
    new_user["password"] = user_data["password"]
    return new_user


@pytest.fixture
def token(test_user):
    return create_access_token({"user_id": test_user["id"]})


@pytest.fixture
def authorized_client(client, token):
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {token}",
    }
    return client


@pytest.fixture
def test_posts(test_user, test_user2, session):
    posts_data = [{
        "title": "first title",
        "content": "first content",
        "owner_id": test_user["id"],
    }, {
        "title": "2nd title",
        "content": "2nd content",
        "owner_id": test_user["id"],
    }, {
        "title": "3rd title",
        "content": "3rd content",
        "owner_id": test_user2["id"],
    }]
    session.add_all([models.Post(**post) for post in posts_data])
    session.commit()
    return session.query(models.Post).all()
