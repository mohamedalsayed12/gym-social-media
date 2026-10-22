"""Add communities and workout photos.

Revision ID: e7b3c2a91d04
Revises: d5f1b8c04e62
Create Date: 2026-10-18 21:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3c2a91d04"
down_revision: Union[str, Sequence[str], None] = "d5f1b8c04e62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workouts", sa.Column("photo_name", sa.String(length=80), nullable=True))
    op.create_table(
        "communities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.UniqueConstraint("slug", name="uq_communities_slug"),
    )
    op.create_table(
        "community_members",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "community_id",
            sa.Integer(),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.UniqueConstraint("user_id", "community_id", name="uq_community_member"),
    )


def downgrade() -> None:
    op.drop_table("community_members")
    op.drop_table("communities")
    op.drop_column("workouts", "photo_name")
