"""Add bodyweight and height to users.

Revision ID: d5f1b8c04e62
Revises: c4e8a1d92b17
Create Date: 2026-10-18 20:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5f1b8c04e62"
down_revision: Union[str, Sequence[str], None] = "c4e8a1d92b17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bodyweight_kg", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "height_cm")
    op.drop_column("users", "bodyweight_kg")
