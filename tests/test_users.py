from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.config import settings
from app.schemas.user import Token

API = "/api/v1"


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_user(client):
    res = client.post(
        f"{API}/users/",
        json={
            "email": "lifter@example.com",
            "username": "lifter",
            "password": "password123",
            "bodyweight_kg": 60,
            "height_cm": 170,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "lifter@example.com"
    assert body["username"] == "lifter"
    assert body["bodyweight_kg"] == 60
    assert body["height_cm"] == 170
    assert "password" not in body


def test_create_user_requires_body_measurements(client):
    res = client.post(
        f"{API}/users/",
        json={"email": "lifter@example.com", "username": "lifter", "password": "password123"},
    )
    assert res.status_code == 422


def test_create_user_duplicate_email(client, test_user):
    res = client.post(
        f"{API}/users/",
        json={
            "email": test_user["email"],
            "username": "someoneelse",
            "password": "password123",
            "bodyweight_kg": 70,
            "height_cm": 175,
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Email is already registered"


def test_create_user_duplicate_username(client, test_user):
    res = client.post(
        f"{API}/users/",
        json={
            "email": "other@example.com",
            "username": test_user["username"],
            "password": "password123",
            "bodyweight_kg": 70,
            "height_cm": 175,
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Username is already taken"


def test_get_me(authorized_client, test_user):
    res = authorized_client.get(f"{API}/users/me")
    assert res.status_code == 200
    assert res.json()["email"] == test_user["email"]
    assert res.json()["username"] == test_user["username"]


def test_get_me_requires_login(client):
    res = client.get(f"{API}/users/me")
    assert res.status_code == 401


def test_public_profile_hides_email(authorized_client, test_user2):
    res = authorized_client.get(f"{API}/users/{test_user2['id']}")
    assert res.status_code == 200
    assert res.json() == {"id": test_user2["id"], "username": test_user2["username"]}


def test_login_user(client, test_user):
    res = client.post(
        f"{API}/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    login_res = Token(**res.json())
    payload = jwt.decode(login_res.access_token, settings.secret_key, algorithms=[settings.algorithm])
    assert res.status_code == 200
    assert payload["sub"] == str(test_user["id"])
    assert payload["type"] == "access"
    assert login_res.refresh_token


def test_login_with_email(client, test_user):
    res = client.post(
        f"{API}/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    assert res.status_code == 200


@pytest.mark.parametrize(
    ("username", "password", "status_code"),
    [
        ("wrong", "password123", 401),
        ("mohamed", "wrongpassword", 401),
        (None, "password123", 422),
        ("mohamed", None, 422),
    ],
)
def test_incorrect_login(test_user, client, username, password, status_code):
    res = client.post(f"{API}/login", data={"username": username, "password": password})
    assert res.status_code == status_code


def test_refresh_token(client, test_user):
    login = client.post(
        f"{API}/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    refresh_token = login.json()["refresh_token"]
    res = client.post(f"{API}/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    me = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.status_code == 200


def test_access_token_rejected_as_refresh(client, token):
    res = client.post(f"{API}/refresh", json={"refresh_token": token})
    assert res.status_code == 401
    assert res.json()["detail"] == "Could not validate credentials"


def test_follow_and_unfollow(authorized_client, test_user, test_user2):
    followed = authorized_client.post(f"{API}/users/{test_user2['id']}/follow")
    assert followed.status_code == 201
    again = authorized_client.post(f"{API}/users/{test_user2['id']}/follow")
    assert again.status_code == 409
    removed = authorized_client.delete(f"{API}/users/{test_user2['id']}/follow")
    assert removed.status_code == 204
    missing = authorized_client.delete(f"{API}/users/{test_user2['id']}/follow")
    assert missing.status_code == 404
    self_follow = authorized_client.post(f"{API}/users/{test_user['id']}/follow")
    assert self_follow.status_code == 400


def test_expired_token(client, test_user):
    expired = jwt.encode(
        {
            "sub": str(test_user["id"]),
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    res = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has expired"
