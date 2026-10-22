"""The signed-in browser session: log a bench workout, then a second account tries to edit it."""

import pytest

BENCH = {
    "notes": "paused reps",
    "performed_at": "2026-10-18T09:00:00Z",
    "visibility": "public",
    "exercises": [
        {
            "name": "Bench press",
            "muscle_group": "chest",
            "sets": [{"reps": 8, "weight": 80}],
        }
    ],
}


def _signup_and_login(client, email, username):
    created = client.post(
        "/users/",
        json={
            "email": email,
            "username": username,
            "password": "password123",
            "bodyweight_kg": 75,
            "height_cm": 178,
        },
    )
    assert created.status_code == 201
    login = client.post("/login", data={"username": username, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def owner(client):
    return _signup_and_login(client, "lifter@example.com", "lifter")


@pytest.fixture
def rejected_workout(client, owner):
    rejected = client.post(
        "/workouts/",
        json={
            "performed_at": "2026-10-18T09:00:00Z",
            "exercises": [{"name": "Bench press", "muscle_group": "chest", "sets": [{}]}],
        },
        headers=owner,
    )
    assert rejected.status_code == 422
    missing = rejected.text.lower()
    assert "sets" in missing
    assert "reps" in missing
    assert "weight" in missing
    return rejected


@pytest.fixture
def bench_workout(client, owner, rejected_workout):
    created = client.post("/workouts/", json=BENCH, headers=owner)
    assert created.status_code == 201
    workout = created.json()
    assert workout["exercises"][0]["name"] == "Bench press"
    assert workout["liked_by_me"] is False
    return workout


@pytest.fixture
def guest(client, bench_workout):
    return _signup_and_login(client, "guest@example.com", "guest")


def test_bench_session_from_signup_through_delete(client, owner, bench_workout, guest):
    workout_id = bench_workout["id"]

    found = client.get("/feed/?exercise=Bench", headers=owner)
    assert found.status_code == 200
    assert [item["id"] for item in found.json()] == [workout_id]

    liked = client.post(f"/workouts/{workout_id}/like", headers=owner)
    assert liked.status_code == 200
    assert liked.json()["likes"] == 1
    assert liked.json()["liked_by_me"] is True

    unliked = client.delete(f"/workouts/{workout_id}/like", headers=owner)
    assert unliked.status_code == 200
    assert unliked.json()["likes"] == 0
    assert unliked.json()["liked_by_me"] is False

    opened = client.get(f"/workouts/{workout_id}", headers=guest)
    assert opened.status_code == 200
    assert opened.json()["exercises"][0]["name"] == "Bench press"
    edited_by_guest = client.patch(
        f"/workouts/{workout_id}",
        json={"notes": "not yours"},
        headers=guest,
    )
    assert edited_by_guest.status_code == 403
    assert edited_by_guest.json()["detail"] == "You can only edit your own workouts"

    edited = client.patch(
        f"/workouts/{workout_id}",
        json={"notes": "added a pause"},
        headers=owner,
    )
    assert edited.status_code == 200
    assert edited.json()["notes"] == "added a pause"
    assert edited.json()["exercises"][0]["sets"][0]["reps"] == 8

    deleted = client.delete(f"/workouts/{workout_id}", headers=owner)
    assert deleted.status_code == 204
    assert client.get(f"/workouts/{workout_id}", headers=owner).status_code == 404
    assert client.get("/feed/?exercise=Bench", headers=owner).json() == []
