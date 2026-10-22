"""add workout fields to posts

Revision ID: a9c3e1b74d20
Revises: 51bdfc328d44
Create Date: 2026-10-18 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9c3e1b74d20"
down_revision: Union[str, Sequence[str], None] = "51bdfc328d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("exercise", sa.String(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "posts",
        sa.Column("sets", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "posts",
        sa.Column("reps", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "posts",
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("posts", "weight")
    op.drop_column("posts", "reps")
    op.drop_column("posts", "sets")
    op.drop_column("posts", "exercise")
