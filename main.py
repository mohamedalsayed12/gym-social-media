import auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import vote
from routers import follows, posts, users, workouts


origins = ["*"]

app = FastAPI(
    title="Gym Social Media API",
    description=(
        "Backend for a gym social app: log workouts, track personal records, "
        "follow other lifters, and post and vote on updates."
    ),
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(vote.router)
app.include_router(workouts.router)
app.include_router(follows.router)


@app.get("/")
def root():
    return {"message": "Gym Social Media API. See /docs for the endpoints."}
