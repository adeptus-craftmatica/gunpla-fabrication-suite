"""create build_planner_supply_usages table

Revision ID: a3111023aa93
Revises: 0ad64bdb8f27
Create Date: 2026-07-31 10:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3111023aa93"
down_revision: str | None = "0ad64bdb8f27"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "build_planner_supply_usages",
        sa.Column("build_project_id", sa.String(), nullable=False),
        sa.Column("supply_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_used", sa.Float(), nullable=False),
        sa.Column("unit_snapshot", sa.String(length=20), nullable=False),
        sa.Column("unit_cost_cents_snapshot", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_cents", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["build_project_id"], ["build_planner_projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_build_planner_supply_usages_build_project_id"),
        "build_planner_supply_usages",
        ["build_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_build_planner_supply_usages_supply_id"),
        "build_planner_supply_usages",
        ["supply_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_build_planner_supply_usages_supply_id"),
        table_name="build_planner_supply_usages",
    )
    op.drop_index(
        op.f("ix_build_planner_supply_usages_build_project_id"),
        table_name="build_planner_supply_usages",
    )
    op.drop_table("build_planner_supply_usages")
