"""add foreign key to users table

Revision ID: 50e2b5386323
Revises: 7c50e9abd188
Create Date: 2026-10-15 08:46:56.405489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50e2b5386323'
down_revision: Union[str, Sequence[str], None] = '7c50e9abd188'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('posts', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'post_users_fk', source_table='posts', referent_table='users',
        local_cols=['owner_id'], remote_cols=['id'],
        ondelete='CASCADE',
    )
    op.create_table(
        'votes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'post_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('post_users_fk', 'posts', type_='foreignkey')
    op.drop_table('votes')
    op.drop_column('posts', 'owner_id')
