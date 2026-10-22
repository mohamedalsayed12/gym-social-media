"""Replace posts and votes with gym workouts.

Revision ID: c4e8a1d92b17
Revises: a9c3e1b74d20
Create Date: 2026-10-18 19:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1d92b17"
down_revision: Union[str, Sequence[str], None] = "a9c3e1b74d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _username_for(email: str, user_id: int, used: set[str]) -> str:
    local = email.split("@", 1)[0]
    cleaned = "".join(char for char in local if char.isalnum() or char == "_")[:24] or "user"
    candidate = cleaned if len(cleaned) >= 3 else f"user_{user_id}"
    if candidate in used:
        candidate = f"{cleaned[:20]}_{user_id}"
    used.add(candidate)
    return candidate


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, email FROM users ORDER BY id")).fetchall()
    used: set[str] = set()
    for row in rows:
        username = _username_for(row.email, row.id, used)
        connection.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": username, "id": row.id},
        )
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("muscle_group", sa.String(length=40), nullable=False),
        sa.UniqueConstraint("name", name="uq_exercises_name"),
    )
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visibility", sa.String(length=16), server_default="public", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "visibility IN ('public', 'followers', 'private')",
            name="ck_workouts_visibility",
        ),
    )
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_exercise_id", sa.Integer(), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["workout_exercise_id"], ["workout_exercises.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "likes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "workout_id"),
    )
    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("following_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "following_id"),
        sa.UniqueConstraint("follower_id", "following_id", name="uq_follows_pair"),
    )

    op.drop_table("votes")
    op.drop_table("posts")


def downgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("exercise", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("sets", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("reps", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE", name="post_users_fk"),
    )
    op.create_table(
        "votes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "post_id"),
    )
    op.drop_table("follows")
    op.drop_table("likes")
    op.drop_table("sets")
    op.drop_table("workout_exercises")
    op.drop_table("workouts")
    op.drop_table("exercises")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
