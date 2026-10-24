"""create posts table

Revision ID: 8b7dada28b71
Revises: 3d11303d49da
Create Date: 2026-10-15 08:20:46.605056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8b7dada28b71'
down_revision: Union[str, Sequence[str], None] = '3d11303d49da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Posts already exist in the preceding revision."""
    pass


def downgrade() -> None:
    op.drop_table('users')
    pass
