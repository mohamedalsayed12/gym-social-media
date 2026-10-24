"""Empty placeholder kept so existing databases can still find this revision.

Revision ID: b60ced0da1d9
Revises: 8b7dada28b71
Create Date: 2026-10-15 08:30:31.366108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b60ced0da1d9'
down_revision: Union[str, Sequence[str], None] = '8b7dada28b71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
