# Music Social Media API

A small social feed backend built with FastAPI. People can create accounts, sign in, publish posts, and vote on posts. There is no frontend yet, but you can explore the API through FastAPI's interactive docs.

The interesting part is how the pieces fit together: users own their posts, votes belong to individual users, and the database enforces those relationships.

## What it does

- Registers users and hashes their passwords before storing them.
- Issues JWT access tokens through `POST /login`.
- Lets signed-in users create, search, list, update, and delete posts. A user can only change or delete their own posts.
- Lets users vote once per post and remove their own vote. Post responses include vote counts.
- Supports pagination on the post list with `limit` and `skip`.

FastAPI serves interactive API documentation at `/docs` when the app is running.

## Built with

FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, pytest, Docker, and GitHub Actions. The repository also contains a Heroku deployment workflow.

## Run with Docker

Create an ignored `.env` file in the project root with `DATABASE_PASSWORD` and a long random `SECRET_KEY`. The database name, username, token algorithm, and token lifetime use the defaults in `docker-compose.prod.yaml` unless you set them explicitly.

Then run:

```bash
docker compose -f docker-compose.prod.yaml up -d --build
docker compose -f docker-compose.prod.yaml exec web alembic upgrade head
```

The API will be at `http://localhost:8000`, with documentation at `http://localhost:8000/docs`. The compose file starts PostgreSQL alongside the API and keeps database records in a named volume.

## Run the tests

Tests need a **separate PostgreSQL database** whose name ends in `_test`. Make sure your local configuration also points to a reachable PostgreSQL server, set `TEST_DATABASE_URL` to the separate database's connection URL, then run:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The test fixtures recreate the application's tables, so never point `TEST_DATABASE_URL` at a database containing data you want to keep. GitHub Actions starts its own PostgreSQL service and runs the suite on every push and pull request.

## How the code is organised

`routers/` handles posts and users, `auth.py` handles login, and `vote.py` handles voting. `schemas.py` defines request and response shapes. `models.py` and `database.py` contain the SQLAlchemy models and session setup; `alembic/` holds database migrations. `tests/` covers authentication, post ownership, pagination, and voting.

This is a backend project in its current form. A frontend or a more specific community theme can be built on top of the API.
