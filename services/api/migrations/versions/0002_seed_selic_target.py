"""Seed catalog: BCB source, Brazil geographic unit and SELIC_TARGET indicator.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21

Only indicators whose metadata was verified against the official source are seeded.
DBGG_GDP and IPCA_12M will be added by their own migrations when implemented.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO data_sources (acronym, name, organization, base_url, documentation_url)
            VALUES ('BCB', 'Sistema Gerenciador de Séries Temporais (SGS)',
                    'Banco Central do Brasil', 'https://api.bcb.gov.br/dados/serie',
                    'https://dadosabertos.bcb.gov.br/')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO geographic_units (ibge_code, acronym, name, geographic_level, parent_id)
            VALUES ('1', 'BR', 'Brasil', 'country', NULL)
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
                'SELIC_TARGET',
                'Taxa de juros - Meta Selic definida pelo Copom',
                'Meta Selic',
                :description,
                id, '432',
                'https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom',
                '% a.a.', 'p.p.', 'daily', 'country', :methodology, 'SGS 432', DATE '1999-03-05'
            FROM data_sources WHERE acronym = 'BCB'
            """
        ),
        {
            "description": (
                "Meta para a taxa Selic definida pelo Comitê de Política Monetária (Copom) do "
                "Banco Central, em percentual ao ano. É a taxa básica de referência da política "
                "monetária."
            ),
            "methodology": (
                "Série SGS 432 do Banco Central do Brasil (fonte: Copom; publicação: BCB/Demab), "
                "disponível desde 05/03/1999. A série é diária e traz um valor para todo dia "
                "corrido, inclusive fins de semana e feriados, igual à meta vigente naquela data; "
                "cada mudança vale a partir do dia seguinte à reunião do Copom. O BCB publica "
                "antecipadamente a meta vigente até a próxima reunião; esses dias futuros não são "
                "armazenados (a coleta vai até a data da coleta). Na visualização mensal, mostra-se "
                "a meta vigente no último dia de cada mês (ou na data da última atualização, no mês "
                "corrente), sem médias. Não confundir com a Selic efetiva (taxa over, séries SGS 11 "
                "e 1178)."
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM indicators WHERE code = 'SELIC_TARGET'"))
    conn.execute(sa.text("DELETE FROM geographic_units WHERE ibge_code = '1'"))
    conn.execute(sa.text("DELETE FROM data_sources WHERE acronym = 'BCB'"))
