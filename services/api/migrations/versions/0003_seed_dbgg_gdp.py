"""Seed catalog: DBGG_GDP indicator (BCB SGS 13762).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21

Metadata validated against the official dataset and API by the economist agent:
SGS 13762 = SGS 13761 (gross general government debt, R$ million, end of month)
/ SGS 4382 (12-month accumulated GDP at current prices) x 100.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO indicators (
                code, name, short_name, description, source_id, source_series_code, source_url,
                unit, change_unit, frequency, geographic_level, methodology,
                methodology_version, first_available_date
            )
            SELECT
                'DBGG_GDP',
                'Dívida bruta do governo geral (% PIB) - Metodologia utilizada a partir de 2008',
                'Dívida bruta (DBGG)',
                :description,
                id, '13762',
                'https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008',
                '% do PIB', 'p.p.', 'monthly', 'country', :methodology,
                'SGS 13762 (metodologia a partir de 2008)', DATE '2006-12-01'
            FROM data_sources WHERE acronym = 'BCB'
            """
        ),
        {
            "description": (
                "Dívida bruta do governo geral (governo federal, INSS, estados e municípios) em "
                "proporção do PIB, segundo a metodologia do Banco Central em vigor desde 2008. "
                "Posição de fim de mês."
            ),
            "methodology": (
                "Saldo de fim de mês da dívida bruta do governo geral dividido pelo PIB acumulado "
                "nos 12 meses até o mês de referência, a preços correntes (BCB/Depec, SGS 13762 = "
                "SGS 13761 / SGS 4382). Inclui as operações compromissadas do Banco Central e "
                "exclui as empresas estatais e os títulos em poder de órgãos públicos. Nos meses "
                "recentes, o PIB é estimado pelo BCB e a razão pode ser revista quando o IBGE "
                "publica as Contas Nacionais; por isso a série inteira é recoletada a cada "
                "atualização. A série não é diretamente comparável à metodologia até 2007 "
                "(SGS 4537) nem ao conceito de dívida bruta do FMI. Variações são expressas em "
                "pontos percentuais (p.p.) do PIB."
            ),
        },
    )


def downgrade() -> None:
    # Observations and runs referencing the indicator must go first (FKs).
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM observation_revisions WHERE observation_id IN (
                SELECT o.id FROM observations o JOIN indicators i ON i.id = o.indicator_id
                WHERE i.code = 'DBGG_GDP')
            """
        )
    )
    for table in ("observations", "ingestion_runs"):
        conn.execute(
            sa.text(
                f"DELETE FROM {table} WHERE indicator_id = "
                "(SELECT id FROM indicators WHERE code = 'DBGG_GDP')"
            )
        )
    conn.execute(sa.text("DELETE FROM indicators WHERE code = 'DBGG_GDP'"))
