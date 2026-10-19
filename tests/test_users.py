import schemas
import pytest
from uuid import uuid4
from jose import jwt
from config import settings






# def test_root(client):
#     res = client.get("/")
#     assert res.json().get("message") == "Hello World"


@pytest.fixture
def created_user(client,test_user):
    email = f"hello123+{uuid4().hex}@example.com"
    res = client.post(
        "/users/", json={"email": email, "password": "password123"}
    )
    assert res.status_code == 201
    new_user = schemas.UserOut(**res.json())
    assert new_user.email == email
    return new_user


def test_create_user(created_user):
    assert created_user.id > 0


def test_create_user_duplicate_email(client, test_user):
    res = client.post(
        "/users/",
        json={"email": test_user["email"], "password": "another-password"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Email is already registered"


def test_get_own_user(authorized_client, test_user):
    res = authorized_client.get(f"/users/{test_user['id']}")
    assert res.status_code == 200
    assert res.json()["email"] == test_user["email"]


def test_get_another_user_forbidden(authorized_client, test_user2):
    res = authorized_client.get(f"/users/{test_user2['id']}")
    assert res.status_code == 403


def test_get_user_requires_login(client, test_user):
    res = client.get(f"/users/{test_user['id']}")
    assert res.status_code == 401


def test_login_user(client, test_user):
    res = client.post(
        "/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    login_res = schemas.Token(**res.json())
    payload = jwt.decode(
        login_res.access_token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    id = (payload.get("user_id"))
    assert res.status_code == 200


@pytest.mark.parametrize("email, password, status_code", [
    ("wrongemail@example.com", "password123", 403),
    ("user@example.com", "wrongpassword", 403),
    ("wrongemail@example.com", "wrongpassword", 403),
    (None, "password123", 422),
    ("user@example.com", None, 422),
])
def test_incorrect_login(test_user, client, email, password, status_code):
    res = client.post(
        "/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == status_code
