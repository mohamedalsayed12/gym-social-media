import models
import schemas
import pytest 

def test_get_all_posts(authorized_client, test_posts):
    res = authorized_client.get("/posts/")

    def validate(post):
        return schemas.PostOut(**post)

    posts_map = map(validate, res.json())
    posts_list = list(posts_map)
    assert len(res.json()) == len(test_posts)
    assert res.status_code == 200
    assert {post.Post.id for post in posts_list} == {post.id for post in test_posts}
    assert [post.Post.id for post in posts_list] == sorted(
        (post.id for post in test_posts), reverse=True
    )


def test_get_posts_pagination(authorized_client, test_posts):
    res = authorized_client.get("/posts/?limit=1&skip=1")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["Post"]["id"] == sorted(
        (post.id for post in test_posts), reverse=True
    )[1]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "skip=-1"])
def test_get_posts_rejects_invalid_pagination(authorized_client, query):
    res = authorized_client.get(f"/posts/?{query}")
    assert res.status_code == 422


def test_unauthorized_user_get_all_posts(client, test_posts):
    res = client.get("/posts/")
    assert res.status_code == 401



def test_unauthorized_user_get_one_posts(client, test_posts):
    res = client.get(f"/posts/{test_posts[0].id}")
    assert res.status_code == 401


def test_get_one_post_not_exist(authorized_client, test_posts):
    res = authorized_client.get("/posts/88888")
    assert res.status_code == 404


def test_get_one_post(authorized_client, test_posts):
    res = authorized_client.get(f"/posts/{test_posts[0].id}")
    post = schemas.PostOut(**res.json())
    assert post.Post.id == test_posts[0].id


@pytest.mark.parametrize("title, content, published", [
    ("awesome new title", "awesome new content", True),
    ("favorite pizza", "i love pepperoni", False),
    ("tallest skyscrapers", "wahoo", True),
])
def test_create_post(authorized_client, test_user, test_posts, title, content, published):
    res = authorized_client.post(
        "/posts/",
        json={"title": title, "content": content, "published": published},
    )
    created_post = schemas.Post(**res.json())
    assert res.status_code == 201
    assert created_post.title == title
    assert created_post.content == content
    assert created_post.published == published
    assert created_post.owner_id == test_user["id"]


def test_create_post_default_published_true(authorized_client, test_user, test_posts):
    res = authorized_client.post(
        "/posts/", json={"title": "arbitrary title", "content": "aasdfjasdf"}
    )
    created_post = schemas.Post(**res.json())
    assert res.status_code == 201
    assert created_post.title == "arbitrary title"
    assert created_post.content == "aasdfjasdf"
    assert created_post.published is True
    assert created_post.owner_id == test_user["id"]


def test_unauthorized_user_delete_post(client, test_user, test_posts):
    res = client.delete(f"/posts/{test_posts[0].id}")
    assert res.status_code == 401


def test_delete_post_success(authorized_client, test_user, test_posts):
    res = authorized_client.delete(f"/posts/{test_posts[0].id}")
    assert res.status_code == 204


def test_update_post_non_exist(authorized_client, test_user, test_posts):
    res = authorized_client.put(
        "/posts/8000000",
        json={"title": "updated title", "content": "updated content"},
    )
    assert res.status_code == 404


def test_delete_other_user_post(authorized_client, test_user, test_posts):
    res = authorized_client.delete(f"/posts/{test_posts[2].id}")
    assert res.status_code == 403


def test_update_post_success(authorized_client, test_posts):
    data = {"title": "updated title", "content": "updated content"}
    res = authorized_client.put(f"/posts/{test_posts[0].id}", json=data)
    updated_post = schemas.Post(**res.json())
    assert res.status_code == 200
    assert updated_post.title == data["title"]
    assert updated_post.content == data["content"]


def test_update_other_user_post(authorized_client, test_user, test_user2, test_posts):
    data = {
        "title": "updated title",
        "content": "updated content",
        "id": test_posts[2].id,
    }
    res = authorized_client.put(f"/posts/{test_posts[2].id}", json=data)
    assert res.status_code == 403


def test_unauthorized_user_update_post(client, test_user, test_posts):
    res = client.put(
        f"/posts/{test_posts[0].id}",
        json={"title": "updated title", "content": "updated content"},
    )
    assert res.status_code == 401




@pytest.fixture
def other_users_draft(test_user2, session):
    draft = models.Post(
        title="secret plan", content="not ready", published=False, owner_id=test_user2["id"]
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def test_other_users_drafts_are_hidden_from_list(authorized_client, test_posts, other_users_draft):
    res = authorized_client.get("/posts/?limit=100")
    assert res.status_code == 200
    ids = [item["Post"]["id"] for item in res.json()]
    assert other_users_draft.id not in ids
    assert len(ids) == len(test_posts)


def test_other_users_draft_returns_404(authorized_client, other_users_draft):
    assert authorized_client.get(f"/posts/{other_users_draft.id}").status_code == 404


def test_owner_can_see_own_draft(authorized_client, test_user, session):
    draft = models.Post(title="my draft", content="wip", published=False, owner_id=test_user["id"])
    session.add(draft)
    session.commit()
    assert authorized_client.get(f"/posts/{draft.id}").status_code == 200
    ids = [item["Post"]["id"] for item in authorized_client.get("/posts/?limit=100").json()]
    assert draft.id in ids


def test_cannot_vote_on_other_users_draft(authorized_client, other_users_draft):
    res = authorized_client.post("/vote/", json={"post_id": other_users_draft.id, "dir": 1})
    assert res.status_code == 404


def test_search_is_case_insensitive(authorized_client, test_posts):
    res = authorized_client.get("/posts/?search=FIRST")
    assert [item["Post"]["title"] for item in res.json()] == ["first title"]


def test_search_treats_wildcards_literally(authorized_client, test_posts):
    assert authorized_client.get("/posts/?search=%25").json() == []
