# Gym Social Media API

I'm building this as the backend for a gym-focused social app. People can log their workouts, track their personal records, follow other lifters, and post and vote on updates. There isn't a frontend yet, but you can try everything through FastAPI's interactive docs.

I focused on getting the relationships right. Users can only change their own posts and workouts, votes and follows belong to individual users, and the database enforces those links. Follows use a composite primary key, so the same follow can't be stored twice, and a check constraint stops people following themselves.

## What works so far

- Registers users and hashes their passwords before storing them.
- Issues JWT access tokens through `POST /login`.
- Lets signed-in users create, search, list, update, and delete posts. A user can only change or delete their own posts.
- Lets users vote once per post and remove their own vote. Post responses include vote counts.
- Supports pagination on the post list with `limit` and `skip`.
- Logs workouts with their exercises, sets, reps and weight. Exercise names are normalised, so "bench press" and "Bench  Press" count as the same lift.
- Works out personal records per exercise (`GET /workouts/records`): the heaviest set, with more reps winning a tie. It's calculated from the logged sets with a window function rather than stored separately, so it can't drift out of date.
- Lets users follow each other, shows follower and following counts, and builds a feed (`GET /feed`) of published posts from the people you follow.

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

I kept the main pieces separate: `routers/` handles posts, users, workouts and follows, `auth.py` handles login, and `vote.py` handles voting. `schemas.py` defines the request and response shapes. The SQLAlchemy models and sessions live in `models.py` and `database.py`, migrations live in `alembic/`, and `tests/` covers authentication, post ownership, pagination, voting, workouts, personal records, follows and the feed.

This is still a backend project. The next step is a frontend.
