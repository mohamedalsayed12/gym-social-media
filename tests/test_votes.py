import pytest
import models
from oauth2 import create_access_token


@pytest.fixture
def test_vote(test_posts, session, test_user):
    new_vote = models.Vote(post_id=test_posts[2].id, user_id=test_user["id"])
    session.add(new_vote)
    session.commit()
    return new_vote


def test_vote_on_post(authorized_client, test_posts, test_user, session):
    post_id = test_posts[2].id
    res = authorized_client.post(
        "/vote/", json={"post_id": post_id, "dir": 1}
    )
    assert res.status_code == 201
    assert res.json() == {"message": "successfully added vote"}
    assert session.query(models.Vote).filter_by(
        post_id=post_id, user_id=test_user["id"]
    ).count() == 1


def test_vote_twice_post(authorized_client, test_posts, test_vote, session):
    post_id = test_posts[2].id
    res = authorized_client.post(
        "/vote/", json={"post_id": post_id, "dir": 1}
    )
    assert res.status_code == 409
    assert session.query(models.Vote).filter_by(post_id=post_id).count() == 1


def test_delete_vote(authorized_client, test_posts, test_vote, session):
    post_id = test_posts[2].id
    res = authorized_client.post(
        "/vote/", json={"post_id": post_id, "dir": 0}
    )
    assert res.status_code == 201
    assert res.json() == {"message": "successfully removed vote"}
    assert session.query(models.Vote).filter_by(post_id=post_id).count() == 0


def test_vote_on_nonexistent_post(authorized_client):
    res = authorized_client.post("/vote/", json={"post_id": 8000000, "dir": 1})
    assert res.status_code == 404
    assert res.json()["detail"] == "Post does not exist"


def test_delete_vote_that_does_not_exist(authorized_client, test_posts):
    res = authorized_client.post(
        "/vote/", json={"post_id": test_posts[0].id, "dir": 0}
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Vote does not exist"


@pytest.mark.parametrize("direction", [0, 1])
def test_unauthorized_user_cannot_vote(client, test_posts, direction):
    res = client.post(
        "/vote/", json={"post_id": test_posts[0].id, "dir": direction}
    )
    assert res.status_code == 401


@pytest.mark.parametrize("direction", [-1, 2])
def test_vote_rejects_invalid_direction(authorized_client, test_posts, direction):
    res = authorized_client.post(
        "/vote/", json={"post_id": test_posts[0].id, "dir": direction}
    )
    assert res.status_code == 422


@pytest.mark.parametrize("payload", [{"dir": 1}, {"post_id": 1}])
def test_vote_requires_both_fields(authorized_client, payload):
    res = authorized_client.post("/vote/", json=payload)
    assert res.status_code == 422


def test_another_user_can_vote_on_same_post(
    authorized_client, test_posts, test_user2, test_vote, session
):
    post_id = test_posts[2].id
    second_token = create_access_token({"user_id": test_user2["id"]})
    res = authorized_client.post(
        "/vote/",
        json={"post_id": post_id, "dir": 1},
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert res.status_code == 201
    assert session.query(models.Vote).filter_by(post_id=post_id).count() == 2


def test_user_cannot_remove_another_users_vote(
    authorized_client, test_posts, test_user2, test_vote, session
):
    post_id = test_posts[2].id
    second_token = create_access_token({"user_id": test_user2["id"]})
    res = authorized_client.post(
        "/vote/",
        json={"post_id": post_id, "dir": 0},
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert res.status_code == 404
    assert session.query(models.Vote).filter_by(post_id=post_id).count() == 1
