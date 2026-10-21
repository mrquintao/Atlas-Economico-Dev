from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

# Precision large enough for rates, ratios and monetary stocks (R$ trillions with decimals).
ECONOMIC_VALUE = Numeric(24, 8)


class Observation(TimestampMixin, Base):
    """One official value of an indicator for a geographic unit at a reference date."""

    __tablename__ = "observations"
    __table_args__ = (
        # Also serves as the main lookup index (indicator, geography, date range).
        UniqueConstraint("indicator_id", "geographic_unit_id", "reference_date"),
        Index("ix_observations_reference_date", "reference_date"),
        # Serves the period-end range filter of every observations query (ADR 0005).
        Index(
            "ix_observations_indicator_geo_period_end",
            "indicator_id",
            "geographic_unit_id",
            "period_end",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    geographic_unit_id: Mapped[int] = mapped_column(ForeignKey("geographic_units.id"))
    reference_date: Mapped[date] = mapped_column(Date)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(ECONOMIC_VALUE)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class IngestionRun(Base):
    """Audit log of each connector execution."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    indicator_id: Mapped[int | None] = mapped_column(ForeignKey("indicators.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ObservationRevision(Base):
    """Records when an official source changes a previously published value."""

    __tablename__ = "observation_revisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), index=True
    )
    previous_value: Mapped[Decimal] = mapped_column(ECONOMIC_VALUE)
    new_value: Mapped[Decimal] = mapped_column(ECONOMIC_VALUE)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
