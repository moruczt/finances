"""insert user2

Revision ID: 3e4d950811e2
Revises: 70433cf26f96
Create Date: 2026-05-08 00:38:28.760938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e4d950811e2'
down_revision: Union[str, Sequence[str], None] = '70433cf26f96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
