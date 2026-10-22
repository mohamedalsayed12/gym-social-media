# Cursor prompt — LiftLog gym social frontend

Paste everything below the line into Cursor (Agent mode), from the root of a new `frontend/` folder.

---

You are building the frontend for **LiftLog**, a gym social media app. The backend is an existing FastAPI app (Python, PostgreSQL, SQLAlchemy, JWT auth). Build a production-quality frontend that talks to it.

## Stack
- React 18 + Vite + TypeScript (strict mode)
- Tailwind CSS
- React Router v6
- TanStack Query for all server state (caching, loading, error, optimistic updates)
- React Hook Form + Zod for forms and validation
- Recharts for progress charts
- No UI kit — build small reusable components in `src/components/ui/` (Button, Input, Card, Modal, Tabs, Avatar, EmptyState, Spinner, Toast)

## Design direction
- Dark theme by default (near-black background `#0e0f11`, surfaces `#17191c`, borders `#2a2e33`), with a light theme toggle.
- One accent colour: chalk-lime `#d4ff3a`, used sparingly (primary buttons, active states, PR badges).
- Fonts: "Archivo Black" (uppercase) for headings, "Archivo" for body (Google Fonts).
- Mobile-first. Bottom tab bar on mobile (Feed / My Workouts / Communities / Profile), left sidebar on desktop (≥1024px).
- Every list has a loading skeleton, an empty state, and an error state with retry.

## Project structure
```
src/
  api/          client.ts (fetch wrapper), one file per resource (auth, posts, votes, workouts, communities)
  api/mock/     mock handlers for endpoints the backend doesn't have yet
  hooks/        TanStack Query hooks (usePosts, useWorkouts, useCommunities, ...)
  components/   ui/ + feature components
  pages/        Login, Register, Feed, Workouts, WorkoutDetail, Communities, CommunityDetail, Profile
  types/        TypeScript types matching the API schemas below
  lib/          auth (token storage, JWT decode), formatting (dates, kg/lb)
```

## API client rules
- Base URL from `VITE_API_URL` (default `http://localhost:8000`).
- Attach `Authorization: Bearer <token>` to every request when logged in.
- On 401: clear the token and redirect to `/login`.
- Surface the backend's `detail` field as the error message.
- Add a `VITE_USE_MOCKS` flag. When true, OR when an endpoint is listed under "Not built yet" below, route the call to `src/api/mock/` which returns realistic data with the exact shapes defined here (in-memory store, ~200ms delay). Each mocked endpoint must be swappable for the real one by changing a single line.

## Existing backend endpoints (real — use these exactly)
- `POST /users/` — register. Body `{ email, password }` → `{ id, email }`. 409 if email taken.
- `POST /login` — **form-urlencoded**, fields `username` (the email) and `password` → `{ access_token, token_type }`. The JWT payload contains `user_id` and `exp`.
- `GET /users/{id}` — only works for the current user → `{ id, email }`.
- `GET /posts/?limit=10&skip=0&search=` — auth required → `[{ Post: { id, title, content, published, created_at, owner_id, owner: { id, email } }, votes: number }]`. Note the capital `Post` key.
- `POST /posts/` — `{ title, content, published }` → Post.
- `PUT /posts/{id}` — same body, owner only (403 otherwise).
- `DELETE /posts/{id}` — 204, owner only.
- `POST /vote/` — `{ post_id, dir: 1 | 0 }`. 1 = like, 0 = unlike. 409 if already liked, 404 if unliking something not liked. The API does **not** tell you whether the current user has liked a post — track liked post ids client-side (persist per user in localStorage) and resync on 409/404.

## Not built yet (mock these, matching these contracts exactly — I will build them in FastAPI)

### Workouts (personal tracking)
- `GET /workouts/?limit&skip&from&to` → `Workout[]` (current user's only)
- `POST /workouts/` → `Workout`
- `GET /workouts/{id}`, `PUT /workouts/{id}`, `DELETE /workouts/{id}`
- `GET /workouts/stats` → `{ total_workouts, workouts_this_week, current_streak_days, total_volume_kg, prs: PR[] }`
- `GET /exercises/{name}/history` → `[{ date, best_weight_kg, best_reps, estimated_1rm_kg }]`

```ts
type Workout = {
  id: number; owner_id: number; name: string;            // "Push day"
  performed_at: string; duration_minutes: number | null; notes: string | null;
  exercises: { id: number; name: string; order: number;
               sets: { id: number; reps: number; weight_kg: number; rpe: number | null }[] }[];
  created_at: string;
};
```

### Communities and PRs
- `GET /communities/?search=` → `Community[]`
- `POST /communities/` → `Community` (creator becomes admin)
- `GET /communities/{id}` → `Community`
- `POST /communities/{id}/join`, `DELETE /communities/{id}/join`
- `GET /communities/{id}/prs?exercise=&limit&skip` → `PR[]` (newest first)
- `POST /communities/{id}/prs` → `PR` (members only, 403 otherwise)
- `GET /communities/{id}/leaderboard?exercise=` → `[{ rank, user: { id, email }, weight_kg, reps, estimated_1rm_kg }]`

```ts
type Community = { id: number; name: string; description: string; member_count: number;
                   is_member: boolean; created_at: string; };
type PR = { id: number; user: { id: number; email: string }; community_id: number | null;
            exercise: string; weight_kg: number; reps: number; estimated_1rm_kg: number;
            video_url: string | null; notes: string | null; achieved_at: string; votes: number; };
```
Estimated 1RM = Epley: `weight * (1 + reps / 30)`, rounded to 0.5kg. Compute it client-side for previews.

## Pages and features

### 1. Auth (`/login`, `/register`)
- Email + password, Zod validation, show backend errors inline. Register logs you in automatically after success.
- Protected routes redirect to `/login`; logged-in users hitting `/login` go to `/`.

### 2. Home feed (`/`)
- Infinite-scroll feed of everyone's posts (`GET /posts/`, page size 10, `skip` pagination).
- Composer at the top: post type chips (Workout / PR / Progress / Question), title, notes, public/private toggle. Until the backend has a `type` column, store the type as a title prefix like `[PR] Deadlift 220kg` and parse it back out for display as a badge.
- **"Share a workout"** button in the composer opens a picker of the user's logged workouts; selecting one pre-fills the title with the workout name and the content with a formatted summary (exercise — sets × reps @ weight).
- Post card: avatar (initials), handle (email before @), relative time, type badge, title, content (preserve line breaks), like button ("💪 Respect" with count, optimistic update), edit/delete for own posts.
- Debounced search bar (300ms) using the `search` param.

### 3. My Workouts (`/workouts`)
- Stats row at the top: workouts this week, current streak, total volume, number of PRs.
- Calendar heatmap of the last 12 weeks (one cell per day, shaded by volume).
- List of workouts, newest first; click → `/workouts/:id` detail.
- **Log workout** flow (full-screen modal on mobile): name, date, then add exercises (autocomplete from a common list + previously used names), each with dynamic sets (reps, weight kg, optional RPE). "Copy last session" button per exercise that pre-fills from that exercise's most recent sets. Show a live total volume. Save, edit, delete.
- Exercise progress: pick an exercise → Recharts line chart of estimated 1RM over time from `/exercises/{name}/history`.
- kg/lb toggle in settings; store everything as kg, convert for display only.

### 4. Communities (`/communities`, `/communities/:id`)
- Browse/search communities, tabs for "Joined" and "Discover". Join/leave button with optimistic update. "Create community" modal (name, description).
- Community detail page with tabs:
  - **PRs**: feed of PRs posted in this community, filterable by exercise, with like buttons.
  - **Leaderboard**: exercise selector (Squat, Bench, Deadlift, OHP + custom) → ranked table by estimated 1RM. Highlight the current user's row.
  - **About**: description, member count, created date.
- **Post a PR** (members only; non-members see a "Join to post" prompt): exercise, weight, reps, date, optional video URL and notes. Show the calculated estimated 1RM live as they type. If it beats the user's previous best for that exercise, show a "New PR 🏆" celebration state before submitting. Option to also share it to the home feed (creates a `[PR]` post via `POST /posts/`).

### 5. Profile (`/profile`)
- Email/handle, join date, stats from `/workouts/stats`, best PR per main lift, list of communities joined, the user's own posts. Logout button and theme/unit settings.

## Quality bar
- Strict TypeScript, no `any`. Types in `src/types/` match the contracts above exactly.
- Accessible: real `<button>`/`<label>` elements, focus states, keyboard-navigable modals, alt text, sufficient contrast in both themes.
- Escape all user content (React default — never use `dangerouslySetInnerHTML`).
- Add a README section: how to run (`npm i`, `npm run dev`), env vars, and a table of which endpoints are real vs mocked.
- Write Vitest tests for: the API client (401 handling, error parsing), the 1RM calculation, the title-prefix type parser, and the like-toggle resync logic.

## Build order
1. Scaffold, Tailwind theme, UI components, API client, auth pages. Verify login works against the real backend.
2. Home feed with the real posts/vote endpoints.
3. Mock layer, then My Workouts.
4. Communities, PRs and leaderboard.
5. Profile, polish, tests, README.

Stop after each step and tell me what you built and how to check it before moving on.
