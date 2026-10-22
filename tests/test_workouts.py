from datetime import UTC, datetime

WORKOUT = {
    "notes": "easy session",
    "performed_at": "2026-10-18T09:00:00Z",
    "visibility": "public",
    "exercises": [
        {
            "name": "Bench press",
            "muscle_group": "chest",
            "sets": [{"reps": 8, "weight": 80}, {"reps": 6, "weight": 85}],
        }
    ],
}


def test_create_and_read_workout(authorized_client, test_user):
    created = authorized_client.post("/workouts/", json=WORKOUT)
    assert created.status_code == 201
    body = created.json()
    assert body["owner"] == {"id": test_user["id"], "username": test_user["username"]}
    assert "owner_id" not in body
    assert body["likes"] == 0
    assert body["liked_by_me"] is False
    assert body["exercises"][0]["name"] == "Bench press"
    assert body["exercises"][0]["sets"][0]["is_pr"] is True
    assert body["exercises"][0]["sets"][1]["is_pr"] is True

    fetched = authorized_client.get(f"/workouts/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_patch_notes_only(authorized_client):
    created = authorized_client.post("/workouts/", json=WORKOUT).json()
    res = authorized_client.patch(f"/workouts/{created['id']}", json={"notes": "added a belt"})
    assert res.status_code == 200
    assert res.json()["notes"] == "added a belt"
    assert res.json()["exercises"][0]["name"] == "Bench press"


def test_cannot_edit_someone_elses_workout(authorized_client, client, test_user2):
    other = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    token = other.json()["access_token"]
    created = client.post(
        "/workouts/",
        json=WORKOUT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    res = authorized_client.patch(f"/workouts/{created.json()['id']}", json={"notes": "nope"})
    assert res.status_code == 403
    assert res.json()["detail"] == "You can only edit your own workouts"


def test_delete_workout(authorized_client):
    created = authorized_client.post("/workouts/", json=WORKOUT).json()
    res = authorized_client.delete(f"/workouts/{created['id']}")
    assert res.status_code == 204
    assert authorized_client.get(f"/workouts/{created['id']}").status_code == 404


def test_like_and_unlike(authorized_client, client, test_user2):
    owner_login = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    created = client.post(
        "/workouts/",
        json=WORKOUT,
        headers={"Authorization": f"Bearer {owner_login.json()['access_token']}"},
    ).json()
    liked = authorized_client.post(f"/workouts/{created['id']}/like")
    assert liked.status_code == 200
    assert liked.json()["likes"] == 1
    assert liked.json()["liked_by_me"] is True

    again = authorized_client.post(f"/workouts/{created['id']}/like")
    assert again.status_code == 409

    cleared = authorized_client.delete(f"/workouts/{created['id']}/like")
    assert cleared.status_code == 200
    assert cleared.json()["likes"] == 0
    assert cleared.json()["liked_by_me"] is False

    missing = authorized_client.delete(f"/workouts/{created['id']}/like")
    assert missing.status_code == 404


def test_private_workout_is_hidden(authorized_client, client, test_user2):
    owner_login = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    payload = {**WORKOUT, "visibility": "private"}
    created = client.post(
        "/workouts/",
        json=payload,
        headers={"Authorization": f"Bearer {owner_login.json()['access_token']}"},
    )
    assert authorized_client.get(f"/workouts/{created.json()['id']}").status_code == 404


def test_later_heavier_set_is_a_personal_record(authorized_client):
    first = {**WORKOUT, "performed_at": "2026-10-01T09:00:00Z"}
    first["exercises"] = [{"name": "Squat", "muscle_group": "legs", "sets": [{"reps": 5, "weight": 100}]}]
    second = {**WORKOUT, "performed_at": "2026-10-08T09:00:00Z"}
    second["exercises"] = [
        {
            "name": "Squat",
            "muscle_group": "legs",
            "sets": [{"reps": 3, "weight": 90}, {"reps": 1, "weight": 120}],
        }
    ]
    third = {**WORKOUT, "performed_at": "2026-10-15T09:00:00Z"}
    third["exercises"] = [{"name": "Squat", "muscle_group": "legs", "sets": [{"reps": 5, "weight": 110}]}]
    assert authorized_client.post("/workouts/", json=first).status_code == 201
    heavier = authorized_client.post("/workouts/", json=second)
    assert heavier.json()["exercises"][0]["sets"][0]["is_pr"] is False
    assert heavier.json()["exercises"][0]["sets"][1]["is_pr"] is True
    lighter = authorized_client.post("/workouts/", json=third)
    assert lighter.json()["exercises"][0]["sets"][0]["is_pr"] is False


def test_rejects_missing_sets(authorized_client):
    payload = {
        "performed_at": datetime.now(UTC).isoformat(),
        "exercises": [{"name": "Row", "muscle_group": "back", "sets": []}],
    }
    res = authorized_client.post("/workouts/", json=payload)
    assert res.status_code == 422


def test_feed_filters_and_visibility(authorized_client, client, test_user, test_user2):
    owner_login = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    public = {
        **WORKOUT,
        "performed_at": "2026-10-10T09:00:00Z",
        "visibility": "public",
        "exercises": [{"name": "Deadlift", "muscle_group": "back", "sets": [{"reps": 3, "weight": 140}]}],
    }
    hidden = {
        **WORKOUT,
        "performed_at": "2026-10-11T09:00:00Z",
        "visibility": "followers",
        "exercises": [{"name": "Pull up", "muscle_group": "back", "sets": [{"reps": 8, "weight": 0}]}],
    }
    assert client.post("/workouts/", json=public, headers=headers).status_code == 201
    followers_only = client.post("/workouts/", json=hidden, headers=headers)
    assert followers_only.status_code == 201

    feed = authorized_client.get("/feed/?exercise=dead&muscle_group=back")
    assert feed.status_code == 200
    names = [item["exercises"][0]["name"] for item in feed.json()]
    assert names == ["Deadlift"]

    follow = authorized_client.post(f"/users/{test_user2['id']}/follow")
    assert follow.status_code == 201
    after = authorized_client.get("/feed/?muscle_group=back")
    assert {item["exercises"][0]["name"] for item in after.json()} == {"Deadlift", "Pull up"}

    dated = authorized_client.get(
        "/feed/?performed_from=2026-10-11T00:00:00Z&performed_to=2026-10-11T23:59:59Z"
    )
    assert [item["id"] for item in dated.json()] == [followers_only.json()["id"]]

    own = authorized_client.post("/workouts/", json={**WORKOUT, "visibility": "private"})
    mine = authorized_client.get("/feed/")
    assert own.json()["id"] in [item["id"] for item in mine.json()]
    assert test_user["id"] == own.json()["owner"]["id"]


def test_following_scope_hides_strangers_until_you_follow(authorized_client, client, test_user2):
    owner_login = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    created = client.post("/workouts/", json=WORKOUT, headers=headers)
    assert created.status_code == 201
    before = authorized_client.get("/feed/?scope=following")
    assert created.json()["id"] not in [item["id"] for item in before.json()]
    assert authorized_client.post(f"/users/{test_user2['id']}/follow").status_code == 201
    after = authorized_client.get("/feed/?scope=following")
    assert created.json()["id"] in [item["id"] for item in after.json()]


def test_profile_counts_a_logged_workout(authorized_client):
    payload = {**WORKOUT, "performed_at": datetime.now(UTC).isoformat()}
    assert authorized_client.post("/workouts/", json=payload).status_code == 201
    profile = authorized_client.get("/users/me/profile")
    assert profile.status_code == 200
    body = profile.json()
    assert body["workouts"] >= 1
    assert body["records"][0]["name"] == "Bench press"
    assert body["week"][0]["muscle_group"] == "chest"
    assert body["hits"] == [{"muscle_group": "chest", "hits": 1, "percent": 100}]
    assert body["records"][0]["rank"] == 1
    assert body["records"][0]["lifters"] == 1
    assert body["records"][0]["percentile"] == 100
    assert body["percentile"] == 100
    assert body["rank"] == 1
    assert body["ranked_lifters"] == 1


def test_pr_rank_uses_public_lifts_only(authorized_client, client, test_user, test_user2):
    other = client.post(
        "/login",
        data={"username": test_user2["username"], "password": test_user2["password"]},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    lighter = {
        **WORKOUT,
        "exercises": [{"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 5, "weight": 60}]}],
    }
    hidden = {
        **WORKOUT,
        "visibility": "private",
        "exercises": [{"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 1, "weight": 200}]}],
    }
    assert client.post("/workouts/", json=lighter, headers=headers).status_code == 201
    assert client.post("/workouts/", json=hidden, headers=headers).status_code == 201
    assert authorized_client.post("/workouts/", json=WORKOUT).status_code == 201

    mine = authorized_client.get("/users/me/profile").json()
    bench = mine["records"][0]
    assert bench["weight"] == 85
    assert bench["rank"] == 1
    assert bench["lifters"] == 2
    assert bench["percentile"] == 100
    assert mine["rank"] == 1
    assert mine["percentile"] == 100

    theirs = client.get("/users/me/profile", headers=headers).json()
    their_bench = next(item for item in theirs["records"] if item["name"] == "Bench press")
    assert their_bench["weight"] == 200
    assert their_bench["rank"] == 1
    assert their_bench["percentile"] == 100
    assert theirs["rank"] == 1


def test_same_bar_ranks_the_lighter_and_taller_lifter_first(client):
    def signup(email, username, bodyweight, height):
        created = client.post(
            "/users/",
            json={
                "email": email,
                "username": username,
                "password": "password123",
                "bodyweight_kg": bodyweight,
                "height_cm": height,
            },
        )
        assert created.status_code == 201
        token = client.post("/login", data={"username": username, "password": "password123"}).json()[
            "access_token"
        ]
        return {"Authorization": f"Bearer {token}"}

    def bench(headers):
        payload = {
            **WORKOUT,
            "exercises": [
                {"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 5, "weight": 100}]}
            ],
        }
        assert client.post("/workouts/", json=payload, headers=headers).status_code == 201
        return client.get("/users/me/profile", headers=headers).json()["records"][0]

    light = signup("light@example.com", "light", 60, 175)
    heavy = signup("heavy@example.com", "heavy", 70, 175)
    bench(light)
    heavy_bench = bench(heavy)
    light_bench = client.get("/users/me/profile", headers=light).json()["records"][0]
    assert light_bench["rank"] == 1
    assert heavy_bench["rank"] == 2

    tall = signup("tall@example.com", "tall", 70, 190)
    short = signup("short@example.com", "shorty", 70, 160)
    squat = {
        **WORKOUT,
        "exercises": [{"name": "Squat", "muscle_group": "legs", "sets": [{"reps": 5, "weight": 140}]}],
    }
    assert client.post("/workouts/", json=squat, headers=tall).status_code == 201
    assert client.post("/workouts/", json=squat, headers=short).status_code == 201

    def squat_rank(headers):
        records = client.get("/users/me/profile", headers=headers).json()["records"]
        return next(item["rank"] for item in records if item["name"] == "Squat")

    assert squat_rank(tall) == 1
    assert squat_rank(short) == 2


def test_feed_pagination_rejects_bad_limit(authorized_client):
    assert authorized_client.get("/feed/?limit=0").status_code == 422
    assert authorized_client.get("/feed/?limit=101").status_code == 422
