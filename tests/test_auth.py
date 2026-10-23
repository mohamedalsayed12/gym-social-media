from app.core.rate_limit import limiter

from conftest import signup

API = "/api/v1"


def _login(client, user):
    res = client.post(f"{API}/login", data={"username": user["username"], "password": user["password"]})
    assert res.status_code == 200
    return res.json()


def test_refresh_token_works_once(client, test_user):
    first = _login(client, test_user)["refresh_token"]
    rotated = client.post(f"{API}/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != first

    reused = client.post(f"{API}/refresh", json={"refresh_token": first})
    assert reused.status_code == 401


def test_reusing_a_refresh_token_signs_out_every_session(client, test_user):
    stolen = _login(client, test_user)["refresh_token"]
    current = client.post(f"{API}/refresh", json={"refresh_token": stolen}).json()["refresh_token"]
    assert client.post(f"{API}/refresh", json={"refresh_token": stolen}).status_code == 401
    assert client.post(f"{API}/refresh", json={"refresh_token": current}).status_code == 401


def test_logout_revokes_the_refresh_token(client, test_user):
    refresh_token = _login(client, test_user)["refresh_token"]
    assert client.post(f"{API}/logout", json={"refresh_token": refresh_token}).status_code == 204
    assert client.post(f"{API}/refresh", json={"refresh_token": refresh_token}).status_code == 401
    assert client.post(f"{API}/logout", json={"refresh_token": "not-a-token"}).status_code == 204


def test_login_is_rate_limited(client):
    signup(client, "slow@example.com", "slowdown")
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post(
                f"{API}/login", data={"username": "slowdown", "password": "wrong-password"}
            ).status_code
            for _ in range(6)
        ]
    finally:
        limiter.enabled = False
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


def test_username_change_conflict(authorized_client, test_user2):
    taken = authorized_client.patch(f"{API}/users/me", json={"username": test_user2["username"]})
    assert taken.status_code == 409
    renamed = authorized_client.patch(f"{API}/users/me", json={"username": "new_name"})
    assert renamed.status_code == 200
    assert renamed.json()["username"] == "new_name"
