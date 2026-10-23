"""Behaviour that only shows up under load: query counts, concurrent requests, large histories."""

import threading
from datetime import UTC, datetime, timedelta

import boto3
import pytest
from app.models.user import User
from app.models.workout import Like, Workout
from app.schemas.workout import WorkoutCreate
from app.services import workout_service
from app.services.storage import S3Storage
from moto import mock_aws
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from conftest import login_headers, signup

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _workout(name, weight, when, reps=5, muscle_group="legs", visibility="public"):
    return {
        "performed_at": when,
        "visibility": visibility,
        "exercises": [
            {"name": name, "muscle_group": muscle_group, "sets": [{"reps": reps, "weight": weight}]}
        ],
    }


class QueryCounter:
    def __init__(self, engine):
        self.engine = engine
        self.count = 0

    def _count(self, *_args):
        self.count += 1

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._count)
        return self

    def __exit__(self, *_exc):
        event.remove(self.engine, "before_cursor_execute", self._count)


def test_feed_query_count_does_not_grow_with_page_size(engine, authorized_client):
    def feed_queries(limit):
        with QueryCounter(engine) as counter:
            res = authorized_client.get(f"{API}/feed/?limit={limit}")
        assert res.status_code == 200
        assert len(res.json()["items"]) == limit
        return counter.count

    for day in range(12):
        when = f"2026-10-{day + 1:02d}T09:00:00Z"
        payload = _workout("Squat", 100 + day, when)
        payload["exercises"].append(
            {"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 5, "weight": 80}]}
        )
        assert authorized_client.post(f"{API}/workouts/", json=payload).status_code == 201

    assert feed_queries(2) == feed_queries(12)


def test_feed_pages_with_a_cursor(authorized_client):
    for day in range(1, 6):
        assert (
            authorized_client.post(
                f"{API}/workouts/", json=_workout("Squat", 100, f"2026-10-0{day}T09:00:00Z")
            ).status_code
            == 201
        )

    seen = []
    cursor = None
    while True:
        query = f"{API}/feed/?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = authorized_client.get(query).json()
        seen += [item["performed_at"][:10] for item in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == ["2026-10-05", "2026-10-04", "2026-10-03", "2026-10-02", "2026-10-01"]
    assert authorized_client.get(f"{API}/feed/?cursor=nonsense").status_code == 400


def test_deleting_an_old_workout_recalculates_later_prs(authorized_client):
    heavy = authorized_client.post(
        f"{API}/workouts/", json=_workout("Squat", 150, "2026-10-01T09:00:00Z")
    ).json()
    later = authorized_client.post(
        f"{API}/workouts/", json=_workout("Squat", 120, "2026-10-08T09:00:00Z")
    ).json()
    assert later["exercises"][0]["sets"][0]["is_pr"] is False

    assert authorized_client.delete(f"{API}/workouts/{heavy['id']}").status_code == 204
    refreshed = authorized_client.get(f"{API}/workouts/{later['id']}").json()
    assert refreshed["exercises"][0]["sets"][0]["is_pr"] is True


def test_moving_a_workout_earlier_recalculates_prs(authorized_client):
    first = authorized_client.post(
        f"{API}/workouts/", json=_workout("Squat", 100, "2026-10-01T09:00:00Z")
    ).json()
    second = authorized_client.post(
        f"{API}/workouts/", json=_workout("Squat", 140, "2026-10-08T09:00:00Z")
    ).json()
    moved = authorized_client.patch(
        f"{API}/workouts/{second['id']}", json={"performed_at": "2026-09-01T09:00:00Z"}
    )
    assert moved.json()["exercises"][0]["sets"][0]["is_pr"] is True
    assert (
        authorized_client.get(f"{API}/workouts/{first['id']}").json()["exercises"][0]["sets"][0]["is_pr"]
        is False
    )


def test_catalogue_exercises_keep_their_muscle_group(client):
    signup(client, "one@example.com", "lifter_one")
    signup(client, "two@example.com", "lifter_two")
    one = login_headers(client, "lifter_one")
    two = login_headers(client, "lifter_two")

    wrong = client.post(
        f"{API}/workouts/",
        json=_workout("bench PRESS", 80, "2026-10-01T09:00:00Z", muscle_group="arms"),
        headers=one,
    )
    assert wrong.json()["exercises"][0]["name"] == "Bench press"
    assert wrong.json()["exercises"][0]["muscle_group"] == "chest"

    mine = client.post(
        f"{API}/workouts/",
        json=_workout("Zercher squat", 80, "2026-10-01T09:00:00Z", muscle_group="quads"),
        headers=one,
    ).json()
    theirs = client.post(
        f"{API}/workouts/",
        json=_workout("Zercher squat", 80, "2026-10-01T09:00:00Z", muscle_group="core"),
        headers=two,
    ).json()
    assert mine["exercises"][0]["muscle_group"] == "legs"
    assert theirs["exercises"][0]["muscle_group"] == "core"
    assert mine["exercises"][0]["id"] != theirs["exercises"][0]["id"]

    unknown = client.post(
        f"{API}/workouts/",
        json=_workout("Row", 50, "2026-10-01T09:00:00Z", muscle_group="elbows"),
        headers=one,
    )
    assert unknown.status_code == 422


def test_oversized_photo_is_rejected(authorized_client):
    created = authorized_client.post(
        f"{API}/workouts/", json=_workout("Squat", 100, "2026-10-01T09:00:00Z")
    ).json()
    huge = PNG + b"\x00" * (5 * 1024 * 1024)
    res = authorized_client.post(
        f"{API}/workouts/{created['id']}/photo", files={"file": ("big.png", huge, "image/png")}
    )
    assert res.status_code == 413


def test_profile_rejects_unknown_time_zone(authorized_client):
    assert authorized_client.get(f"{API}/users/me/profile?tz=Mars/Olympus").status_code == 422
    assert authorized_client.get(f"{API}/users/me/profile?tz=Europe/London").status_code == 200


@mock_aws
def test_s3_storage_round_trip():
    boto3.client("s3", region_name="eu-west-2").create_bucket(
        Bucket="gym-social-test", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
    )
    storage = S3Storage("gym-social-test", region="eu-west-2")
    storage.save("lift.png", PNG, "image/png")
    stored = storage.client.get_object(Bucket="gym-social-test", Key="lift.png")
    assert stored["ContentType"] == "image/png"
    assert "lift.png" in storage.url("lift.png")
    assert "Signature" in storage.url("lift.png") or "X-Amz-Signature" in storage.url("lift.png")
    storage.delete("lift.png")
    assert storage.client.list_objects_v2(Bucket="gym-social-test").get("KeyCount") == 0


@pytest.fixture
def committed_workout(engine):
    """Real committed rows, because concurrent requests can't share the rolled-back test transaction."""
    with Session(engine) as db:
        owner = User(email="race@example.com", username="race_owner", password="x", bodyweight_kg=70)
        fan = User(email="fan@example.com", username="race_fan", password="x", bodyweight_kg=70)
        db.add_all([owner, fan])
        db.commit()
        when = datetime.now(UTC) - timedelta(days=1)
        workout = workout_service.create_workout(db, owner, WorkoutCreate(**_workout("Squat", 100, when)))
        ids = (owner.id, fan.id, workout.id)
    yield ids
    with Session(engine) as db:
        db.execute(delete(User).where(User.id.in_(ids[:2])))
        db.commit()


def test_double_tapped_like_is_counted_once(engine, committed_workout):
    _, fan_id, workout_id = committed_workout
    barrier = threading.Barrier(2)
    results, errors = [], []

    def like():
        try:
            with Session(engine) as db:
                fan = db.get(User, fan_id)
                workout = db.get(Workout, workout_id)
                barrier.wait()
                results.append(workout_service.like_workout(db, fan, workout))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=like) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(results) == [False, True]
    with Session(engine) as db:
        assert len(db.scalars(select(Like).where(Like.workout_id == workout_id)).all()) == 1
