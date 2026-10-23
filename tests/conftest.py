import os
import tempfile
from pathlib import Path

os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="gym-social-uploads-")
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.database import build_database_url, get_db  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

API = "/api/v1"
ROOT = Path(__file__).resolve().parents[1]


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


@pytest.fixture(scope="session")
def engine():
    """Build the test schema once, by running the real migrations rather than create_all,
    so a broken migration fails the suite instead of failing a deploy."""
    engine = create_engine(build_test_database_url())
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine):
    """Each test runs inside a transaction that is rolled back afterwards. The app's own
    commits become savepoints, so tests stay isolated without rebuilding the schema."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def signup(client, email, username, bodyweight=70, height=175, password="password123"):
    res = client.post(
        f"{API}/users/",
        json={
            "email": email,
            "username": username,
            "password": password,
            "bodyweight_kg": bodyweight,
            "height_cm": height,
        },
    )
    assert res.status_code == 201
    user = res.json()
    user["password"] = password
    return user


def login_headers(client, username, password="password123"):
    res = client.post(f"{API}/login", data={"username": username, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def test_user(client):
    return signup(client, "mohamedalsayed@gmail.com", "mohamed", bodyweight=70, height=180)


@pytest.fixture
def test_user2(client):
    return signup(client, "nora@example.com", "nora", bodyweight=60, height=170)


@pytest.fixture
def token(test_user):
    return create_access_token(test_user["id"])


@pytest.fixture
def authorized_client(client, token):
    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return client
