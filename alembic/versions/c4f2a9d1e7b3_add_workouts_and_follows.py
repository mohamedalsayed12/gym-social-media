"""add workouts, workout exercises and follows

Revision ID: c4f2a9d1e7b3
Revises: 51bdfc328d44
Create Date: 2026-10-19 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f2a9d1e7b3"
down_revision: Union[str, Sequence[str], None] = "51bdfc328d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workouts_owner_id", "workouts", ["owner_id"])

    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("exercise", sa.String(), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=False),
        sa.CheckConstraint("sets > 0", name="ck_workout_exercises_sets_positive"),
        sa.CheckConstraint("reps > 0", name="ck_workout_exercises_reps_positive"),
        sa.CheckConstraint("weight_kg >= 0", name="ck_workout_exercises_weight_non_negative"),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_exercises_workout_id", "workout_exercises", ["workout_id"])

    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followed_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("follower_id <> followed_id", name="ck_follows_not_self"),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followed_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "followed_id"),
    )


def downgrade() -> None:
    op.drop_table("follows")
    op.drop_index("ix_workout_exercises_workout_id", table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index("ix_workouts_owner_id", table_name="workouts")
    op.drop_table("workouts")
