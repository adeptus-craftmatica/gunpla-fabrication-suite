"""create supplies_items table

Revision ID: 0ad64bdb8f27
Revises: a6b1a7fcdd52
Create Date: 2026-07-31 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0ad64bdb8f27"
down_revision: str | None = "a6b1a7fcdd52"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplies_items",
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("color_name", sa.String(length=120), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("quantity_on_hand", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("low_stock_threshold", sa.Float(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price_cents", sa.Integer(), nullable=True),
        sa.Column("tags_csv", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("supplies_items")
