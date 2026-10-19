import pytest

import models
from oauth2 import create_access_token


def _workout(title="Push day", performed_on="2026-10-01", exercises=None):
    return {
        "title": title,
        "performed_on": performed_on,
        "notes": "Felt strong",
        "exercises": exercises
        or [
            {"exercise": "bench press", "sets": 3, "reps": 5, "weight_kg": 80},
            {"exercise": "Overhead  Press", "sets": 3, "reps": 8, "weight_kg": 45.5},
        ],
    }


@pytest.fixture
def other_client(client, test_user2):
    from fastapi.testclient import TestClient
    from main import app

    other = TestClient(app)
    other.headers = {
        **other.headers,
        "Authorization": f"Bearer {create_access_token({'user_id': test_user2['id']})}",
    }
    return other


def test_create_workout(authorized_client, test_user):
    res = authorized_client.post("/workouts/", json=_workout())
    assert res.status_code == 201
    body = res.json()
    assert body["owner_id"] == test_user["id"]
    assert body["title"] == "Push day"
    assert [e["exercise"] for e in body["exercises"]] == ["Bench Press", "Overhead Press"]
    assert float(body["exercises"][1]["weight_kg"]) == 45.5


def test_create_workout_requires_auth(client):
    assert client.post("/workouts/", json=_workout()).status_code == 401


@pytest.mark.parametrize(
    "exercise",
    [
        {"exercise": "squat", "sets": 0, "reps": 5, "weight_kg": 100},
        {"exercise": "squat", "sets": 3, "reps": 5, "weight_kg": -1},
        {"exercise": "   ", "sets": 3, "reps": 5, "weight_kg": 100},
    ],
)
def test_create_workout_rejects_invalid_exercise(authorized_client, exercise):
    res = authorized_client.post("/workouts/", json=_workout(exercises=[exercise]))
    assert res.status_code == 422


def test_create_workout_needs_at_least_one_exercise(authorized_client):
    payload = _workout()
    payload["exercises"] = []
    res = authorized_client.post("/workouts/", json=payload)
    assert res.status_code == 422


def test_list_only_returns_own_workouts_newest_first(authorized_client, other_client):
    authorized_client.post("/workouts/", json=_workout("Old", "2026-09-01"))
    authorized_client.post("/workouts/", json=_workout("New", "2026-10-10"))
    other_client.post("/workouts/", json=_workout("Not mine", "2026-10-15"))

    res = authorized_client.get("/workouts/")
    assert res.status_code == 200
    assert [w["title"] for w in res.json()] == ["New", "Old"]


def test_list_workouts_paginates(authorized_client):
    for day in range(1, 4):
        authorized_client.post("/workouts/", json=_workout(f"Day {day}", f"2026-10-0{day}"))
    res = authorized_client.get("/workouts/?limit=1&skip=1")
    assert [w["title"] for w in res.json()] == ["Day 2"]


def test_cannot_view_or_delete_another_users_workout(authorized_client, other_client):
    workout_id = other_client.post("/workouts/", json=_workout()).json()["id"]
    assert authorized_client.get(f"/workouts/{workout_id}").status_code == 403
    assert authorized_client.delete(f"/workouts/{workout_id}").status_code == 403


def test_delete_workout_removes_its_exercises(authorized_client, session):
    workout_id = authorized_client.post("/workouts/", json=_workout()).json()["id"]
    assert authorized_client.delete(f"/workouts/{workout_id}").status_code == 204
    assert authorized_client.get(f"/workouts/{workout_id}").status_code == 404
    session.expire_all()
    assert session.query(models.WorkoutExercise).count() == 0


def test_get_missing_workout_returns_404(authorized_client):
    assert authorized_client.get("/workouts/9999").status_code == 404


def test_personal_records_pick_heaviest_set(authorized_client, other_client):
    authorized_client.post("/workouts/", json=_workout("A", "2026-10-01", [
        {"exercise": "Squat", "sets": 3, "reps": 5, "weight_kg": 100},
        {"exercise": "Deadlift", "sets": 1, "reps": 3, "weight_kg": 140},
    ]))
    authorized_client.post("/workouts/", json=_workout("B", "2026-10-08", [
        {"exercise": "squat", "sets": 2, "reps": 3, "weight_kg": 110},
        {"exercise": "Deadlift", "sets": 1, "reps": 5, "weight_kg": 140},
    ]))
    other_client.post("/workouts/", json=_workout("C", "2026-10-09", [
        {"exercise": "Squat", "sets": 1, "reps": 1, "weight_kg": 250},
    ]))

    res = authorized_client.get("/workouts/records")
    assert res.status_code == 200
    records = {r["exercise"]: r for r in res.json()}
    assert set(records) == {"Deadlift", "Squat"}
    assert float(records["Squat"]["weight_kg"]) == 110
    assert records["Squat"]["performed_on"] == "2026-10-08"
    # same weight, so the set with more reps wins
    assert records["Deadlift"]["reps"] == 5


def test_personal_records_empty_for_new_user(authorized_client):
    res = authorized_client.get("/workouts/records")
    assert res.status_code == 200
    assert res.json() == []
