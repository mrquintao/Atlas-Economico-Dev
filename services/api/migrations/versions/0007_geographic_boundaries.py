"""Store official IBGE boundaries (GeoJSON) of geographic units, versioned by mesh year (S2).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

Geometries are collected by `python -m app.ingestion.cli ingest-boundaries` from the IBGE mesh
API (servicodados.ibge.gov.br/api/v3/malhas); this migration only creates the table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "geographic_boundaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("geographic_unit_id", sa.Integer(), nullable=False),
        sa.Column("mesh_year", sa.Integer(), nullable=False),
        sa.Column("quality", sa.String(length=16), nullable=False),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("geometry_hash", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "quality IN ('minima', 'intermediaria', 'maxima')",
            name=op.f("ck_geographic_boundaries_quality"),
        ),
        sa.ForeignKeyConstraint(
            ["geographic_unit_id"],
            ["geographic_units.id"],
            name=op.f("fk_geographic_boundaries_geographic_unit_id_geographic_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_geographic_boundaries")),
        sa.UniqueConstraint(
            "geographic_unit_id",
            "mesh_year",
            "quality",
            name=op.f("uq_geographic_boundaries_geographic_unit_id_mesh_year_quality"),
        ),
    )


def downgrade() -> None:
    op.drop_table("geographic_boundaries")
