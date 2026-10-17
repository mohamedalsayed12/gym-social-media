import schemas
import pytest
from uuid import uuid4
from jose import jwt
from config import settings






# def test_root(client):
#     res = client.get("/")
#     print(res.json().get("message"))
#     assert res.json().get("message") == "Hello World"


@pytest.fixture
def created_user(client,test_user):
    email = f"hello123+{uuid4().hex}@gmail.com"
    res = client.post(
        "/users/", json={"email": email, "password": "password123"}
    )
    assert res.status_code == 201
    new_user = schemas.UserOut(**res.json())
    assert new_user.email == email
    return new_user


def test_create_user(created_user):
    assert created_user.id > 0


def test_login_user(client, test_user):
    res = client.post(
        "/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    print(res.json())
    login_res = schemas.Token(**res.json())
    payload = jwt.decode(
        login_res.access_token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    id = (payload.get("user_id"))
    assert res.status_code == 200


@pytest.mark.parametrize("email, password, status_code", [
    ("wrongemail@gmail.com", "password123", 403),
    ("sanjeev@gmail.com", "wrongpassword", 403),
    ("wrongemail@gmail.com", "wrongpassword", 403),
    (None, "password123", 422),
    ("sanjeev@gmail.com", None, 422),
])
def test_incorrect_login(test_user, client, email, password, status_code):
    res = client.post(
        "/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == status_code
