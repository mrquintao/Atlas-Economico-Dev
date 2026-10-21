"""SICONFI source and raw fiscal reports (RREO/RGF annexes) of the states (S3).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-21

Reports are collected by `python -m app.ingestion.cli ingest-siconfi` from the SICONFI open-data
API (apidatalake.tesouro.gov.br/ords/siconfi); this migration seeds the source and creates the
tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO data_sources (acronym, name, organization, base_url, documentation_url)
        VALUES ('SICONFI',
                'Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro (SICONFI)',
                'Secretaria do Tesouro Nacional',
                'https://apidatalake.tesouro.gov.br/ords/siconfi/tt',
                'https://apidatalake.tesouro.gov.br/docs/siconfi/')
        """
    )
    op.create_table(
        "fiscal_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("geographic_unit_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=8), nullable=False),
        sa.Column("exercise", sa.Integer(), nullable=False),
        sa.Column("periodicity", sa.String(length=1), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("annex", sa.String(length=64), nullable=False),
        sa.Column("sphere", sa.String(length=1), nullable=False),
        sa.Column("power", sa.String(length=1), nullable=True),
        sa.Column("institution", sa.String(length=255), nullable=True),
        sa.Column("population", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("period BETWEEN 1 AND 6", name=op.f("ck_fiscal_reports_period")),
        sa.CheckConstraint(
            "periodicity IN ('B', 'Q', 'S')", name=op.f("ck_fiscal_reports_periodicity")
        ),
        sa.CheckConstraint(
            "report_type IN ('RREO', 'RGF')", name=op.f("ck_fiscal_reports_report_type")
        ),
        sa.ForeignKeyConstraint(
            ["geographic_unit_id"],
            ["geographic_units.id"],
            name=op.f("fk_fiscal_reports_geographic_unit_id_geographic_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fiscal_reports")),
        sa.UniqueConstraint(
            "geographic_unit_id",
            "report_type",
            "exercise",
            "periodicity",
            "period",
            "annex",
            "sphere",
            "power",
            name="uq_fiscal_reports_identity",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "fiscal_report_rows",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("column", sa.String(length=255), nullable=False),
        sa.Column("account_code", sa.String(length=255), nullable=False),
        sa.Column("account", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["fiscal_reports.id"],
            name=op.f("fk_fiscal_report_rows_report_id_fiscal_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fiscal_report_rows")),
        sa.UniqueConstraint(
            "report_id",
            "label",
            "column",
            "account_code",
            "account",
            name="uq_fiscal_report_rows_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("fiscal_report_rows")
    op.drop_table("fiscal_reports")
    op.execute(
        "DELETE FROM ingestion_runs WHERE source_id = "
        "(SELECT id FROM data_sources WHERE acronym = 'SICONFI')"
    )
    op.execute("DELETE FROM data_sources WHERE acronym = 'SICONFI'")
