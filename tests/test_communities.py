PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

WORKOUT = {
    "notes": "community session",
    "performed_at": "2026-10-18T09:00:00Z",
    "visibility": "public",
    "exercises": [{"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 5, "weight": 100}]}],
}


def _signup(client, email, username, bodyweight):
    created = client.post(
        "/users/",
        json={
            "email": email,
            "username": username,
            "password": "password123",
            "bodyweight_kg": bodyweight,
            "height_cm": 175,
        },
    )
    assert created.status_code == 201
    token = client.post("/login", data={"username": username, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _community(client, headers, slug):
    rows = client.get("/communities/", headers=headers).json()
    return next(item for item in rows if item["slug"] == slug)


def test_defaults_and_a_new_community(authorized_client):
    listed = authorized_client.get("/communities/")
    assert listed.status_code == 200
    slugs = {item["slug"] for item in listed.json()}
    assert {"bodybuilding", "pilates", "powerlifting"} <= slugs

    created = authorized_client.post(
        "/communities/",
        json={"name": "Olympic Lifting", "description": "Snatch and clean & jerk"},
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "olympic-lifting"
    assert created.json()["joined"] is True
    assert created.json()["members"] == 1

    again = authorized_client.post("/communities/", json={"name": "Olympic Lifting"})
    assert again.status_code == 409


def test_each_community_ranks_only_its_members(client):
    light = _signup(client, "light@example.com", "light", 60)
    heavy = _signup(client, "heavy@example.com", "heavy", 80)
    outsider = _signup(client, "out@example.com", "outsider", 50)
    for headers in (light, heavy, outsider):
        assert client.post("/workouts/", json=WORKOUT, headers=headers).status_code == 201
    huge = {
        **WORKOUT,
        "exercises": [{"name": "Bench press", "muscle_group": "chest", "sets": [{"reps": 1, "weight": 200}]}],
    }
    assert client.post("/workouts/", json=huge, headers=outsider).status_code == 201

    assert client.post("/communities/powerlifting/join", headers=light).status_code == 200
    assert client.post("/communities/powerlifting/join", headers=heavy).status_code == 200
    assert client.post("/communities/bodybuilding/join", headers=outsider).status_code == 200

    light_rank = _community(client, light, "powerlifting")
    heavy_rank = _community(client, heavy, "powerlifting")
    assert light_rank["rank"] == 1
    assert light_rank["percentile"] == 100
    assert heavy_rank["rank"] == 2
    assert heavy_rank["ranked_lifters"] == 2
    assert _community(client, outsider, "bodybuilding")["rank"] == 1
    assert _community(client, light, "bodybuilding")["joined"] is False

    assert client.delete("/communities/powerlifting/join", headers=heavy).status_code == 204
    assert _community(client, light, "powerlifting")["ranked_lifters"] == 1


def test_workout_photo_is_served(authorized_client):
    created = authorized_client.post("/workouts/", json=WORKOUT)
    assert created.status_code == 201
    workout_id = created.json()["id"]
    uploaded = authorized_client.post(
        f"/workouts/{workout_id}/photo",
        files={"file": ("lift.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200
    photo_url = uploaded.json()["photo_url"]
    assert photo_url.startswith("/media/")
    assert authorized_client.get(photo_url).status_code == 200

    rejected = authorized_client.post(
        f"/workouts/{workout_id}/photo",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == "Use a JPEG, PNG, or WebP photo"
