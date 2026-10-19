# Gym Social Media API

I'm building this as the backend for a gym-focused social app. Right now it's a post-and-vote API: people can create accounts, sign in, publish posts, and vote. There isn't a frontend or gym-specific content yet, but you can try the API through FastAPI's interactive docs.

I focused on getting the relationships right. Users can only change their own posts, votes belong to individual users, and the database enforces those links.

## What works so far

- Registers users and hashes their passwords before storing them.
- Issues JWT access tokens through `POST /login`.
- Lets signed-in users create, search, list, update, and delete posts. A user can only change or delete their own posts.
- Lets users vote once per post and remove their own vote. Post responses include vote counts.
- Supports pagination on the post list with `limit` and `skip`.

When the app is running, FastAPI's interactive docs are at `/docs`.

## Stack

I used FastAPI, Pydantic, SQLAlchemy, PostgreSQL, and Alembic for the API and database. I added pytest tests, Docker setup, and GitHub Actions. There's also a Heroku deployment workflow in the repo.

## Run it locally

Create an ignored `.env` file in the project root with `DATABASE_PASSWORD` and a long random `SECRET_KEY`. You can leave the database name, username, token algorithm, and token lifetime at the defaults in `docker-compose.prod.yaml`, or set them yourself.

Then run:

```bash
docker compose -f docker-compose.prod.yaml up -d --build
docker compose -f docker-compose.prod.yaml exec web alembic upgrade head
```

The API then runs at `http://localhost:8000`, and you can try it at `http://localhost:8000/docs`. Compose also starts PostgreSQL and keeps its data in a named volume.

## Run the tests

The tests need a **separate PostgreSQL database** with a name ending in `_test`. Make sure PostgreSQL is reachable, set `TEST_DATABASE_URL` to that test database, then run:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test fixtures recreate the application's tables, so don't use a database with data you want to keep. GitHub Actions starts its own PostgreSQL service and runs the tests on every push and pull request.

## How I organised the code

I kept the main pieces separate: `routers/` handles posts and users, `auth.py` handles login, and `vote.py` handles voting. `schemas.py` defines the request and response shapes. The SQLAlchemy models and sessions live in `models.py` and `database.py`, migrations live in `alembic/`, and `tests/` covers authentication, post ownership, pagination, and voting.

This is still a backend project. The next step is a frontend and features specific to a gym community.
