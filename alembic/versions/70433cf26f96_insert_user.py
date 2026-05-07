"""insert user

Revision ID: 70433cf26f96
Revises: a56a5752b06a
Create Date: 2026-05-08 00:31:54.557358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70433cf26f96'
down_revision: Union[str, Sequence[str], None] = 'a56a5752b06a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass

    user_table = sa.table("users",
                        sa.column("username", sa.String),
                        sa.column("password", sa.String))
    op.bulk_insert(user_table, [
                    {"username":"moruczt","password":"$argon2id$v=19$m=65536,t=3,p=4$e2/tfc/5n3OOEWLMuRfiHA$KDvCmFs0GT7onCgu4hxL6rsPrgB6ytH5ZIzAyWfhfkU"},
                    ])


def downgrade() -> None:
    """Downgrade schema."""
    pass
