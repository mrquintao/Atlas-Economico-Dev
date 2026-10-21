from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
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
    """Country/region/state/municipality, identified by its official IBGE code."""

    __tablename__ = "geographic_units"
    __table_args__ = (
        CheckConstraint(
            "geographic_level IN ('country', 'region', 'state', 'municipality')",
            name="geographic_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ibge_code: Mapped[str] = mapped_column(String(16), unique=True)
    acronym: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    geographic_level: Mapped[str] = mapped_column(String(16))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("geographic_units.id"))
