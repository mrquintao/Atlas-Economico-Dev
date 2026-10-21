"""Index observations by (indicator, geography, period_end) for the period-end range filter.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-21

Observations are selected when their reference period ends within the requested range
(ADR 0005); without this index that filter scanned every row of the indicator.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_observations_indicator_geo_period_end",
        "observations",
        ["indicator_id", "geographic_unit_id", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_observations_indicator_geo_period_end", table_name="observations")
