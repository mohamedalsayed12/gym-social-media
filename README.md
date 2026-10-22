# Gym Social

API for logging workouts, following lifters, and liking sessions.

Posts from the course project are workouts. A workout has an owner, notes, a time, and a visibility of `public`, `followers`, or `private`. Each workout lists exercises, and each exercise lists sets with reps and weight in kilograms. A set is a personal record when its weight beats that lifter's previous best for the exercise.

## Layout

```
app/
  main.py
  core/        config and password/token helpers
  db/          engine and declarative base
  models/      User, Exercise, Workout, Set, Follow, Like
  schemas/
  routers/     auth, users, workouts, feed
  services/    database work, including PR detection
tests/
```

Route functions stay thin. Queries and writes live in `app/services/`.

## Run

Copy `.env.example` to `.env` and point it at Postgres.

```bash
docker compose -f docker-compose.dev.yaml up --build
```

Or, with Postgres already running:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

`GET /health` returns `{"status": "ok"}`.

The React app lives in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The UI is a phone-sized LIFTLOG screen: dark feed, set-by-set logger, and a profile with weekly volume and records. The dev server proxies API calls to http://127.0.0.1:8000.

Allowed browser origins come from `CORS_ORIGINS`. The default is the local Vite app, not every origin.

## Auth

Register with `POST /users/` and a JSON body of `email`, `username`, and `password`. Passwords are hashed with Argon2.

`POST /login` takes form fields `username` (email or username) and `password`. The response includes an access token and a refresh token. Send `Authorization: Bearer <access_token>` on later requests. `POST /refresh` accepts `{"refresh_token": "..."}`. An expired token returns `401` with `"Token has expired"`.

`GET /users/me` returns the signed-in user. `GET /users/{id}` returns `{id, username}` and does not include the email.

## Workouts and feed

`POST /workouts/` accepts notes, `performed_at`, visibility, and exercises:

```json
{
  "notes": "easy session",
  "performed_at": "2026-10-18T09:00:00Z",
  "visibility": "public",
  "exercises": [
    {
      "name": "Bench press",
      "muscle_group": "chest",
      "sets": [{"reps": 8, "weight": 80}]
    }
  ]
}
```

The response is flat: `id`, `notes`, `performed_at`, `visibility`, `owner` (`id` and `username`), `exercises`, `likes`, and `liked_by_me`. `PATCH /workouts/{id}` updates only the fields you send. Delete, like, and unlike are on the same path.

`GET /feed/` filters with `exercise`, `muscle_group`, `performed_from`, and `performed_to`, and pages with `limit` and `skip`.

## Tests

```bash
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest
```

Coverage from the latest local run: **94%**.
cle_group`, `performed_from`, and `performed_to`, and pages with `limit` and `skip`.

## Tests

```bash
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest
```

Coverage from the latest local run: **94%**.
