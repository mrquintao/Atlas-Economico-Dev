"""Seed catalog: IBGE source and IPCA_12M indicator (SIDRA table 1737, variable 2265).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

Validated against the official API (apisidra.ibge.gov.br/values/t/1737/n1/all/v/all/p/last 1):
variable 2265 = "IPCA - Variação acumulada em 12 meses" (unit code 2 = %). Not to be confused
with 63 (monthly), 69 (year to date), 2263/2264 (3 and 6 months) or 2266 (index number).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO data_sources (acronym, name, organization, base_url, documentation_url)
            VALUES ('IBGE', 'Sistema IBGE de Recuperação Automática (SIDRA)',
                    'Instituto Brasileiro de Geografia e Estatística',
                    'https://apisidra.ibge.gov.br', 'https://apisidra.ibge.gov.br/home/ajuda')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO indicators (
                code, name, short_name, description, source_id, source_series_code, source_url,
                unit, change_unit, frequency, geographic_level, methodology,
                methodology_version, first_available_date
            )
            SELECT
                'IPCA_12M',
                'IPCA - Variação acumulada em 12 meses',
                'IPCA 12 meses',
                :description,
                id, '1737/2265',
                'https://sidra.ibge.gov.br/tabela/1737',
                '%', 'p.p.', 'monthly', 'country', :methodology,
                'SIDRA 1737, variável 2265', DATE '1980-12-01'
            FROM data_sources WHERE acronym = 'IBGE'
            """
        ),
        {
            "description": (
                "Inflação medida pelo Índice Nacional de Preços ao Consumidor Amplo (IPCA), "
                "acumulada nos 12 meses até o mês de referência. É o índice usado como medida "
                "oficial da inflação no Brasil."
            ),
            "methodology": (
                "Tabela 1737 do SIDRA/IBGE, variável 2265 (IPCA - Variação acumulada em 12 "
                "meses), Brasil. Cada observação é a variação do índice de preços entre o mês "
                "de referência e o mesmo mês do ano anterior, ou seja, o produto das 12 "
                "variações mensais até o mês de referência. A data da observação é o mês de "
                "referência; a janela de 12 meses começa, portanto, até 11 meses antes do "
                "início de qualquer período filtrado. Não é a variação mensal nem a "
                "acumulada no ano. Para os meses anteriores a dezembro de 1980 o IBGE não "
                "divulga o acumulado em 12 meses ('...'); eles aparecem como lacunas. "
                "Variações entre dois meses são expressas em pontos percentuais (p.p.)."
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM observation_revisions WHERE observation_id IN (
                SELECT o.id FROM observations o JOIN indicators i ON i.id = o.indicator_id
                WHERE i.code = 'IPCA_12M')
            """
        )
    )
    for table in ("observations", "ingestion_runs"):
        conn.execute(
            sa.text(
                f"DELETE FROM {table} WHERE indicator_id = "
                "(SELECT id FROM indicators WHERE code = 'IPCA_12M')"
            )
        )
    conn.execute(sa.text("DELETE FROM indicators WHERE code = 'IPCA_12M'"))
    conn.execute(sa.text("DELETE FROM data_sources WHERE acronym = 'IBGE'"))
