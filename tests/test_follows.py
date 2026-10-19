import models


def test_follow_user(authorized_client, test_user, test_user2, session):
    res = authorized_client.post(f"/users/{test_user2['id']}/follow")
    assert res.status_code == 201
    assert session.query(models.Follow).filter_by(
        follower_id=test_user["id"], followed_id=test_user2["id"]
    ).count() == 1


def test_cannot_follow_yourself(authorized_client, test_user):
    assert authorized_client.post(f"/users/{test_user['id']}/follow").status_code == 400


def test_cannot_follow_missing_user(authorized_client):
    assert authorized_client.post("/users/9999/follow").status_code == 404


def test_cannot_follow_twice(authorized_client, test_user2):
    authorized_client.post(f"/users/{test_user2['id']}/follow")
    assert authorized_client.post(f"/users/{test_user2['id']}/follow").status_code == 409


def test_follow_requires_auth(client, test_user2):
    assert client.post(f"/users/{test_user2['id']}/follow").status_code == 401


def test_unfollow_user(authorized_client, test_user2, session):
    authorized_client.post(f"/users/{test_user2['id']}/follow")
    assert authorized_client.delete(f"/users/{test_user2['id']}/follow").status_code == 204
    assert session.query(models.Follow).count() == 0


def test_unfollow_when_not_following(authorized_client, test_user2):
    assert authorized_client.delete(f"/users/{test_user2['id']}/follow").status_code == 404


def test_follow_stats(authorized_client, test_user, test_user2):
    authorized_client.post(f"/users/{test_user2['id']}/follow")
    them = authorized_client.get(f"/users/{test_user2['id']}/follow-stats").json()
    me = authorized_client.get(f"/users/{test_user['id']}/follow-stats").json()
    assert (them["followers"], them["following"]) == (1, 0)
    assert (me["followers"], me["following"]) == (0, 1)


def test_feed_shows_only_followed_users_published_posts(
    authorized_client, test_user, test_user2, test_posts, session
):
    session.add(models.Post(
        title="draft", content="hidden", published=False, owner_id=test_user2["id"]
    ))
    session.commit()

    assert authorized_client.get("/feed").json() == []

    authorized_client.post(f"/users/{test_user2['id']}/follow")
    res = authorized_client.get("/feed")
    assert res.status_code == 200
    titles = [item["Post"]["title"] for item in res.json()]
    assert titles == ["3rd title"]
    assert res.json()[0]["votes"] == 0


def test_feed_paginates(authorized_client, test_user2, session):
    session.add_all([
        models.Post(title=f"post {n}", content="c", owner_id=test_user2["id"])
        for n in range(3)
    ])
    session.commit()
    authorized_client.post(f"/users/{test_user2['id']}/follow")
    assert len(authorized_client.get("/feed?limit=2").json()) == 2
    assert len(authorized_client.get("/feed?limit=2&skip=2").json()) == 1
