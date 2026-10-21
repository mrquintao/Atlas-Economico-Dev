from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class DataSource(TimestampMixin, Base):
    """An official data provider (e.g. Banco Central do Brasil)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    acronym: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(512))
    documentation_url: Mapped[str | None] = mapped_column(String(512))

    indicators: Mapped[list["Indicator"]] = relationship(back_populates="source")


class Indicator(TimestampMixin, Base):
    """Catalog entry for an indicator. New indicators are rows here, never new tables."""

    __tablename__ = "indicators"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('daily', 'monthly', 'quarterly', 'annual')", name="frequency"
        ),
        CheckConstraint(
            "geographic_level IN ('country', 'region', 'state', 'municipality')",
            name="geographic_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    source_series_code: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(512))
    unit: Mapped[str] = mapped_column(String(64))
    # Unit used to express the difference between two observations (e.g. "p.p." for rates).
    change_unit: Mapped[str] = mapped_column(String(32))
    frequency: Mapped[str] = mapped_column(String(16))
    geographic_level: Mapped[str] = mapped_column(String(16))
    methodology: Mapped[str] = mapped_column(Text)
    methodology_version: Mapped[str | None] = mapped_column(String(64))
    first_available_date: Mapped[date | None] = mapped_column(Date)

    source: Mapped[DataSource] = relationship(back_populates="indicators")


class GeographicUnit(Base):
    """Country/region/state/municipality, identified by its official IBGE code.

    IBGE codes and acronyms are unique only within a level (Brasil and the Norte region are both
    code 1; SE is both the Sudeste region and the state of Sergipe).
    """

    __tablename__ = "geographic_units"
    __table_args__ = (
        CheckConstraint(
            "geographic_level IN ('country', 'region', 'state', 'municipality')",
            name="geographic_level",
        ),
        UniqueConstraint("geographic_level", "ibge_code"),
        UniqueConstraint("geographic_level", "acronym"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ibge_code: Mapped[str] = mapped_column(String(16))
    acronym: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(128))
    geographic_level: Mapped[str] = mapped_column(String(16))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("geographic_units.id"))

    parent: Mapped["GeographicUnit | None"] = relationship(remote_side=[id])


class GeographicBoundary(TimestampMixin, Base):
    """Official IBGE boundary (GeoJSON geometry) of a unit in one mesh edition and quality.

    Versioned by ``mesh_year`` (the IBGE ``periodo``); re-collecting the same edition updates the
    geometry only when the IBGE changed it (``geometry_hash``).
    """

    __tablename__ = "geographic_boundaries"
    __table_args__ = (
        UniqueConstraint("geographic_unit_id", "mesh_year", "quality"),
        CheckConstraint("quality IN ('minima', 'intermediaria', 'maxima')", name="quality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    geographic_unit_id: Mapped[int] = mapped_column(ForeignKey("geographic_units.id"))
    mesh_year: Mapped[int] = mapped_column(Integer)
    quality: Mapped[str] = mapped_column(String(16))
    geometry: Mapped[dict[str, Any]] = mapped_column(JSONB)
    geometry_hash: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(512))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    geographic_unit: Mapped[GeographicUnit] = relationship()
