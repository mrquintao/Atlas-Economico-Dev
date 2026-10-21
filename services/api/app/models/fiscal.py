from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.catalog import GeographicUnit
from app.models.observation import ECONOMIC_VALUE


class FiscalReport(TimestampMixin, Base):
    """One annex of a SICONFI report (RREO or RGF) of an entity for one period, as published.

    Raw layer (S3): rows are stored exactly as served (``fiscal_report_rows``); fiscal indicators
    are derived from them later (S4). ``content_hash`` identifies the published content, so a
    rectification by the entity is detected as a hash change. ``power`` is NULL for the RREO,
    which is consolidated for the whole entity.
    """

    __tablename__ = "fiscal_reports"
    __table_args__ = (
        UniqueConstraint(
            "geographic_unit_id",
            "report_type",
            "exercise",
            "periodicity",
            "period",
            "annex",
            "sphere",
            "power",
            name="uq_fiscal_reports_identity",  # the conventional name exceeds 63 characters
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("report_type IN ('RREO', 'RGF')", name="report_type"),
        CheckConstraint("periodicity IN ('B', 'Q', 'S')", name="periodicity"),
        CheckConstraint("period BETWEEN 1 AND 6", name="period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    geographic_unit_id: Mapped[int] = mapped_column(ForeignKey("geographic_units.id"))
    report_type: Mapped[str] = mapped_column(String(8))
    exercise: Mapped[int] = mapped_column(Integer)
    periodicity: Mapped[str] = mapped_column(String(1))
    period: Mapped[int] = mapped_column(Integer)
    annex: Mapped[str] = mapped_column(String(64))
    sphere: Mapped[str] = mapped_column(String(1))
    power: Mapped[str | None] = mapped_column(String(1))
    institution: Mapped[str | None] = mapped_column(String(255))
    population: Mapped[int | None] = mapped_column(BigInteger)
    row_count: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    # Latest delivery or rectification listed by `extrato_entregas` when collected.
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(1024))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    geographic_unit: Mapped[GeographicUnit] = relationship()
    rows: Mapped[list["FiscalReportRow"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class FiscalReportRow(Base):
    """One published value of a SICONFI report annex (one rotulo, coluna and conta)."""

    __tablename__ = "fiscal_report_rows"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "label",
            "column",
            "account_code",
            "account",
            name="uq_fiscal_report_rows_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("fiscal_reports.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(255))
    column: Mapped[str] = mapped_column(String(255))
    account_code: Mapped[str] = mapped_column(String(255))
    account: Mapped[str] = mapped_column(Text)
    value: Mapped[Decimal] = mapped_column(ECONOMIC_VALUE)

    report: Mapped[FiscalReport] = relationship(back_populates="rows")
