"""quick add budgets

Revision ID: 8c1f4e2a9b7d
Revises: 20f9d283e642
Create Date: 2026-10-26 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c1f4e2a9b7d'
down_revision: Union[str, Sequence[str], None] = '20f9d283e642'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    budget_table = op.create_table("budgets",
                                   sa.Column("id", sa.Integer(), nullable=False),
                                   sa.Column("name", sa.String(length=50), nullable=False),
                                   sa.Column("monthly_limit", sa.Numeric(precision=20, scale=4), server_default="0", nullable=False),
                                   sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
                                   sa.PrimaryKeyConstraint("id"),
                                   sa.UniqueConstraint("name"))
    op.create_table("manual_entries",
                    sa.Column("id", sa.Integer(), nullable=False),
                    sa.Column("budget_id", sa.Integer(), nullable=False),
                    sa.Column("month", sa.Date(), nullable=False),
                    sa.Column("amount_huf", sa.Numeric(precision=20, scale=4), nullable=False),
                    sa.Column("description", sa.String(length=255), nullable=True),
                    sa.Column("split_group", sa.String(length=36), nullable=True),
                    sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
                    sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"]),
                    sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_manual_entries_month"), "manual_entries", ["month"], unique=False)
    op.create_index(op.f("ix_manual_entries_split_group"), "manual_entries", ["split_group"], unique=False)

    op.bulk_insert(budget_table, [{"name":"Casual"}, {"name":"Extra"}])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_manual_entries_split_group"), table_name="manual_entries")
    op.drop_index(op.f("ix_manual_entries_month"), table_name="manual_entries")
    op.drop_table("manual_entries")
    op.drop_table("budgets")
