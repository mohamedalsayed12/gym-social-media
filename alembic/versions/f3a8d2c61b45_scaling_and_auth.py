"""Store PRs and e1RM on sets, add an exercise catalogue, indexes and refresh tokens.

Revision ID: f3a8d2c61b45
Revises: e7b3c2a91d04
Create Date: 2026-10-23 15:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3a8d2c61b45"
down_revision: str | Sequence[str] | None = "e7b3c2a91d04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MUSCLE_GROUPS = ("chest", "back", "shoulders", "arms", "legs", "core", "full_body")
ALIASES = {
    "pec": "chest", "pecs": "chest",
    "lat": "back", "lats": "back", "traps": "back",
    "shoulder": "shoulders", "delt": "shoulders", "delts": "shoulders",
    "bicep": "arms", "biceps": "arms", "tricep": "arms", "triceps": "arms", "forearms": "arms",
    "quad": "legs", "quads": "legs", "hamstring": "legs", "hamstrings": "legs",
    "glute": "legs", "glutes": "legs", "calf": "legs", "calves": "legs",
    "ab": "core", "abs": "core", "abdominals": "core",
}  # fmt: skip

CATALOGUE = [
    ("Bench press", "chest"), ("Incline bench press", "chest"), ("Dumbbell bench press", "chest"),
    ("Chest fly", "chest"), ("Dip", "chest"),
    ("Deadlift", "back"), ("Barbell row", "back"), ("Pull up", "back"), ("Lat pulldown", "back"),
    ("Seated cable row", "back"),
    ("Overhead press", "shoulders"), ("Dumbbell shoulder press", "shoulders"), ("Lateral raise", "shoulders"),
    ("Face pull", "shoulders"),
    ("Barbell curl", "arms"), ("Dumbbell curl", "arms"), ("Hammer curl", "arms"),
    ("Tricep pushdown", "arms"), ("Skull crusher", "arms"),
    ("Squat", "legs"), ("Front squat", "legs"), ("Leg press", "legs"), ("Romanian deadlift", "legs"),
    ("Bulgarian split squat", "legs"), ("Leg curl", "legs"), ("Leg extension", "legs"),
    ("Hip thrust", "legs"), ("Calf raise", "legs"),
    ("Plank", "core"), ("Hanging leg raise", "core"), ("Cable crunch", "core"),
    ("Clean and jerk", "full_body"), ("Snatch", "full_body"),
]  # fmt: skip

COMMUNITIES = [
    ("bodybuilding", "Bodybuilding", "Hypertrophy, physique, and stage prep."),
    ("pilates", "Pilates", "Control, core, and mobility."),
    ("powerlifting", "Powerlifting", "Squat, bench, and deadlift."),
]


def upgrade() -> None:
    cases = " ".join(
        f"WHEN lower(trim(muscle_group)) = '{alias}' THEN '{region}'" for alias, region in ALIASES.items()
    )
    allowed = ", ".join(f"'{group}'" for group in MUSCLE_GROUPS)
    op.execute(
        f"""
        UPDATE exercises SET muscle_group = CASE
            WHEN lower(trim(muscle_group)) IN ({allowed}) THEN lower(trim(muscle_group))
            {cases}
            ELSE 'full_body'
        END
        """
    )
    op.create_check_constraint("ck_exercises_muscle_group", "exercises", f"muscle_group IN ({allowed})")

    op.execute(
        """
        WITH keep AS (
            SELECT id, min(id) OVER (PARTITION BY lower(name)) AS keep_id FROM exercises
        )
        UPDATE workout_exercises we SET exercise_id = keep.keep_id
        FROM keep WHERE we.exercise_id = keep.id AND keep.id <> keep.keep_id
        """
    )
    op.execute(
        "DELETE FROM exercises e USING exercises other "
        "WHERE lower(e.name) = lower(other.name) AND e.id > other.id"
    )
    op.add_column("exercises", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "exercises_owner_id_fkey", "exercises", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("uq_exercises_name", "exercises", type_="unique")
    op.create_index(
        "uq_exercises_catalogue_name",
        "exercises",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("owner_id IS NULL"),
    )
    op.create_index(
        "uq_exercises_owner_name",
        "exercises",
        ["owner_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )

    op.add_column("sets", sa.Column("e1rm", sa.Float(), server_default=sa.text("0"), nullable=False))
    op.add_column("sets", sa.Column("is_pr", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.execute("UPDATE sets SET e1rm = CASE WHEN reps <= 1 THEN weight ELSE weight * (1 + reps / 30.0) END")
    op.execute(
        """
        UPDATE sets s SET is_pr = s.weight > GREATEST(
            COALESCE((
                SELECT max(s2.weight)
                FROM sets s2
                JOIN workout_exercises we2 ON we2.id = s2.workout_exercise_id
                JOIN workouts w2 ON w2.id = we2.workout_id
                WHERE w2.owner_id = w.owner_id
                  AND we2.exercise_id = we.exercise_id
                  AND w2.performed_at < w.performed_at
            ), -1),
            COALESCE((
                SELECT max(s3.weight) FROM sets s3
                WHERE s3.workout_exercise_id = s.workout_exercise_id AND s3.set_number < s.set_number
            ), -1)
        )
        FROM workout_exercises we
        JOIN workouts w ON w.id = we.workout_id
        WHERE we.id = s.workout_exercise_id
        """
    )

    op.create_index("ix_workouts_owner_performed", "workouts", ["owner_id", "performed_at"])
    op.create_index("ix_workouts_visibility_performed", "workouts", ["visibility", "performed_at", "id"])
    op.create_index("ix_workout_exercises_workout_id", "workout_exercises", ["workout_id"])
    op.create_index("ix_workout_exercises_exercise_id", "workout_exercises", ["exercise_id"])
    op.create_index("ix_sets_workout_exercise_id", "sets", ["workout_exercise_id"])
    op.create_index("ix_likes_workout_id", "likes", ["workout_id"])
    op.create_index("ix_follows_following_id", "follows", ["following_id"])
    op.create_index("ix_community_members_community_id", "community_members", ["community_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    communities = sa.table("communities", sa.column("slug"), sa.column("name"), sa.column("description"))
    for slug, name, description in COMMUNITIES:
        op.execute(
            postgresql.insert(communities)
            .values(slug=slug, name=name, description=description)
            .on_conflict_do_nothing()
        )
    exercises = sa.table("exercises", sa.column("name"), sa.column("muscle_group"))
    for name, muscle_group in CATALOGUE:
        op.execute(
            postgresql.insert(exercises).values(name=name, muscle_group=muscle_group).on_conflict_do_nothing()
        )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    for name, table in (
        ("ix_community_members_community_id", "community_members"),
        ("ix_follows_following_id", "follows"),
        ("ix_likes_workout_id", "likes"),
        ("ix_sets_workout_exercise_id", "sets"),
        ("ix_workout_exercises_exercise_id", "workout_exercises"),
        ("ix_workout_exercises_workout_id", "workout_exercises"),
        ("ix_workouts_visibility_performed", "workouts"),
        ("ix_workouts_owner_performed", "workouts"),
    ):
        op.drop_index(name, table_name=table)
    op.drop_column("sets", "is_pr")
    op.drop_column("sets", "e1rm")
    op.drop_index("uq_exercises_owner_name", table_name="exercises")
    op.drop_index("uq_exercises_catalogue_name", table_name="exercises")
    op.execute("UPDATE exercises SET name = left(name, 70) || ' #' || id WHERE owner_id IS NOT NULL")
    op.create_unique_constraint("uq_exercises_name", "exercises", ["name"])
    op.drop_constraint("exercises_owner_id_fkey", "exercises", type_="foreignkey")
    op.drop_column("exercises", "owner_id")
    op.drop_constraint("ck_exercises_muscle_group", "exercises", type_="check")
