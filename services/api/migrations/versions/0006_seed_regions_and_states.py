"""Seed geographic units: the 5 major regions and the 27 federative units (S1).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-21

Codes, acronyms and names validated against the official IBGE API on 2026-10-21:
servicodados.ibge.gov.br/api/v1/localidades/regioes and .../localidades/estados?orderBy=id
(5 regions, 27 UFs; each UF's region taken from its `regiao.id`).

IBGE codes are unique only within a level: region 1 (Norte) shares its code with Brasil (1), and
region SE (Sudeste) shares its acronym with the state SE (Sergipe). Uniqueness therefore moves from
the single columns to (geographic_level, ibge_code) and (geographic_level, acronym).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (IBGE code, acronym, name)
REGIONS: list[tuple[str, str, str]] = [
    ("1", "N", "Norte"),
    ("2", "NE", "Nordeste"),
    ("3", "SE", "Sudeste"),
    ("4", "S", "Sul"),
    ("5", "CO", "Centro-Oeste"),
]

# (IBGE code, acronym, name, region IBGE code). The first digit of a UF code is its region code.
STATES: list[tuple[str, str, str, str]] = [
    ("11", "RO", "Rondônia", "1"),
    ("12", "AC", "Acre", "1"),
    ("13", "AM", "Amazonas", "1"),
    ("14", "RR", "Roraima", "1"),
    ("15", "PA", "Pará", "1"),
    ("16", "AP", "Amapá", "1"),
    ("17", "TO", "Tocantins", "1"),
    ("21", "MA", "Maranhão", "2"),
    ("22", "PI", "Piauí", "2"),
    ("23", "CE", "Ceará", "2"),
    ("24", "RN", "Rio Grande do Norte", "2"),
    ("25", "PB", "Paraíba", "2"),
    ("26", "PE", "Pernambuco", "2"),
    ("27", "AL", "Alagoas", "2"),
    ("28", "SE", "Sergipe", "2"),
    ("29", "BA", "Bahia", "2"),
    ("31", "MG", "Minas Gerais", "3"),
    ("32", "ES", "Espírito Santo", "3"),
    ("33", "RJ", "Rio de Janeiro", "3"),
    ("35", "SP", "São Paulo", "3"),
    ("41", "PR", "Paraná", "4"),
    ("42", "SC", "Santa Catarina", "4"),
    ("43", "RS", "Rio Grande do Sul", "4"),
    ("50", "MS", "Mato Grosso do Sul", "5"),
    ("51", "MT", "Mato Grosso", "5"),
    ("52", "GO", "Goiás", "5"),
    ("53", "DF", "Distrito Federal", "5"),
]


def upgrade() -> None:
    op.drop_constraint("uq_geographic_units_acronym", "geographic_units", type_="unique")
    op.drop_constraint("uq_geographic_units_ibge_code", "geographic_units", type_="unique")
    op.create_unique_constraint(
        "uq_geographic_units_geographic_level_ibge_code",
        "geographic_units",
        ["geographic_level", "ibge_code"],
    )
    op.create_unique_constraint(
        "uq_geographic_units_geographic_level_acronym",
        "geographic_units",
        ["geographic_level", "acronym"],
    )

    conn = op.get_bind()
    for code, acronym, name in REGIONS:
        conn.execute(
            sa.text(
                """
                INSERT INTO geographic_units (ibge_code, acronym, name, geographic_level, parent_id)
                SELECT :code, :acronym, :name, 'region', id
                FROM geographic_units WHERE geographic_level = 'country' AND ibge_code = '1'
                """
            ),
            {"code": code, "acronym": acronym, "name": name},
        )
    for code, acronym, name, region in STATES:
        conn.execute(
            sa.text(
                """
                INSERT INTO geographic_units (ibge_code, acronym, name, geographic_level, parent_id)
                SELECT :code, :acronym, :name, 'state', id
                FROM geographic_units WHERE geographic_level = 'region' AND ibge_code = :region
                """
            ),
            {"code": code, "acronym": acronym, "name": name, "region": region},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM geographic_units WHERE geographic_level = 'state'"))
    conn.execute(sa.text("DELETE FROM geographic_units WHERE geographic_level = 'region'"))
    op.drop_constraint(
        "uq_geographic_units_geographic_level_acronym", "geographic_units", type_="unique"
    )
    op.drop_constraint(
        "uq_geographic_units_geographic_level_ibge_code", "geographic_units", type_="unique"
    )
    op.create_unique_constraint("uq_geographic_units_ibge_code", "geographic_units", ["ibge_code"])
    op.create_unique_constraint("uq_geographic_units_acronym", "geographic_units", ["acronym"])
