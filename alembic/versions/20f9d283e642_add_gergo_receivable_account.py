"""add gergo receivable account

Revision ID: 20f9d283e642
Revises: e6cfa39ef02b
Create Date: 2026-09-01 15:58:02.376294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from models import AccountSide


# revision identifiers, used by Alembic.
revision: str = '20f9d283e642'
down_revision: Union[str, Sequence[str], None] = 'e6cfa39ef02b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PATH = "Assets:Receiveables:Gergo"
PARENT_PATH = "Assets:Receiveables"


def upgrade() -> None:
    """Upgrade schema."""
    account_side_db_type = ENUM('Assets', 'Liabilities', 'Income', 'Expenses', 'Equity', name='accountside', create_type=False)
    account_table = sa.table("accounts",
                             sa.column("id", sa.Integer),
                             sa.column("parent_id", sa.Integer),
                             sa.column("name", sa.String),
                             sa.column("side", account_side_db_type),
                             sa.column("path", sa.String))

    bind = op.get_bind()
    parent_id = bind.execute(sa.select(account_table.c.id).where(account_table.c.path == PARENT_PATH)).scalar_one()

    op.bulk_insert(account_table, [
        {"parent_id": parent_id, "name": "Gergo", "side": AccountSide.Assets.value, "path": NEW_PATH},
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM accounts WHERE path = :path").bindparams(path=NEW_PATH))
