"""Seed catalog: state fiscal indicators derived from the SICONFI annexes (S4, ADR 0010).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-21

Adds the bimonthly (RREO) and four-monthly (RGF) frequencies and nine state-level indicators.
Each one is a single published row of an annex (account code and column in
app/ingestion/fiscal_catalog.py), validated by the economist against the official API on
2026-10-21. Observations are produced by `python -m app.ingestion.cli derive-fiscal`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_FREQUENCIES = "frequency IN ('daily', 'monthly', 'quarterly', 'annual')"
NEW_FREQUENCIES = (
    "frequency IN ('daily', 'monthly', 'bimonthly', 'quarterly', 'four_monthly', 'annual')"
)
SOURCE_URL = "https://apidatalake.tesouro.gov.br/docs/siconfi/"
BRL = "R$ correntes"

ACCUMULATED_IN_YEAR = (
    "Valores acumulados no ano até o bimestre de referência: a acumulação recomeça a cada "
    "janeiro, por isso bimestres diferentes não são comparáveis entre si (o 1º bimestre soma dois "
    "meses; o 6º, o ano inteiro)."
)
NOMINAL_VALUES = "Valores nominais (R$ correntes), sem correção pela inflação."
EXECUTIVE_ONLY = (
    "Não inclui os demais Poderes e órgãos (Legislativo, Judiciário, Ministério Público, "
    "Defensoria e Tribunal de Contas), que publicam relatórios próprios; os relatórios não são "
    "somados."
)

INDICATORS: list[dict[str, str]] = [
    {
        "code": "STATE_RCL",
        "name": "Receita corrente líquida (RCL) dos estados - últimos 12 meses",
        "short_name": "Receita corrente líquida",
        "description": (
            "Receitas correntes do estado, deduzidas das transferências a municípios, das "
            "contribuições dos servidores ao regime próprio de previdência e da dedução para o "
            "FUNDEB, somadas nos 12 meses encerrados no bimestre de referência."
        ),
        "series": "RREO-Anexo 03 · RREO3ReceitaCorrenteLiquida",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "bimonthly",
        "methodology": (
            "Receita corrente líquida (LRF, art. 2º, IV), como publicada no Anexo 3 do Relatório "
            "Resumido da Execução Orçamentária (RREO) entregue pelo estado ao SICONFI: linha "
            "RREO3ReceitaCorrenteLiquida, coluna 'TOTAL (ÚLTIMOS 12 MESES)'. Cada observação é o "
            "total dos 12 meses encerrados no bimestre de referência; a janela de 12 meses começa "
            "antes do bimestre. É a RCL da LRF, não as versões ajustadas usadas só no cálculo dos "
            "limites de endividamento e de pessoal. No Distrito Federal a RCL inclui receitas de "
            "competência municipal (IPTU, ISS, ITBI). " + NOMINAL_VALUES + " Série a partir do "
            "exercício de 2018."
        ),
        "version": "MDF/STN; RREO Anexo 3, desde 2018",
    },
    {
        "code": "STATE_DC",
        "name": "Dívida consolidada (DC) dos estados - saldo no fim do quadrimestre",
        "short_name": "Dívida consolidada",
        "description": (
            "Total das obrigações financeiras do estado com prazo de amortização superior a 12 "
            "meses, inclusive precatórios vencidos e não pagos, no fim de cada quadrimestre."
        ),
        "series": "RGF-Anexo 02 · DividaConsolidada",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "four_monthly",
        "methodology": (
            "Dívida consolidada (LRF, art. 29), como publicada no Anexo 2 do Relatório de Gestão "
            "Fiscal (RGF) do Poder Executivo, que se refere ao estado inteiro: linha "
            "DividaConsolidada, coluna 'Até o Nº Quadrimestre' do relatório do próprio "
            "quadrimestre. É um saldo (estoque) no último dia do quadrimestre, não um fluxo. Não "
            "inclui o passivo atuarial do regime próprio de previdência, informado à parte no "
            "demonstrativo. " + NOMINAL_VALUES + " Série a partir do exercício de 2018."
        ),
        "version": "MDF/STN; RGF Anexo 2, desde 2018",
    },
    {
        "code": "STATE_DCL",
        "name": "Dívida consolidada líquida (DCL) dos estados - saldo no fim do quadrimestre",
        "short_name": "Dívida consolidada líquida",
        "description": (
            "Dívida consolidada menos a disponibilidade de caixa e os demais haveres financeiros "
            "do estado, no fim de cada quadrimestre. Pode ser negativa."
        ),
        "series": "RGF-Anexo 02 · DividaConsolidadaLiquida",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "four_monthly",
        "methodology": (
            "Dívida consolidada líquida, como publicada no Anexo 2 do RGF do Poder Executivo "
            "(estado inteiro): linha DividaConsolidadaLiquida, coluna 'Até o Nº Quadrimestre' do "
            "relatório do próprio quadrimestre. É a dívida consolidada deduzida da disponibilidade "
            "de caixa (líquida de restos a pagar processados e depósitos restituíveis) e dos "
            "demais haveres financeiros, no último dia do quadrimestre. Valor negativo significa "
            "que os haveres superam a dívida; não é erro de dado. " + NOMINAL_VALUES + " Série a "
            "partir do exercício de 2018."
        ),
        "version": "MDF/STN; RGF Anexo 2, desde 2018",
    },
    {
        "code": "STATE_DCL_RCL",
        "name": "Dívida consolidada líquida sobre a RCL ajustada dos estados (%)",
        "short_name": "DCL / RCL",
        "description": (
            "Relação entre a dívida consolidada líquida e a receita corrente líquida ajustada "
            "para o cálculo dos limites de endividamento, como publicada pelo estado."
        ),
        "series": "RGF-Anexo 02 · PercentualDaDCLSobreARCL",
        "unit": "% da RCL ajustada",
        "change_unit": "p.p.",
        "frequency": "four_monthly",
        "methodology": (
            "Percentual publicado no Anexo 2 do RGF do Poder Executivo (linha "
            "PercentualDaDCLSobreARCL, coluna 'Até o Nº Quadrimestre' do relatório do próprio "
            "quadrimestre), sem recálculo pelo Atlas. O denominador é a RCL dos 12 meses "
            "encerrados no quadrimestre, ajustada para o cálculo dos limites de endividamento "
            "(sem as transferências da União de emendas parlamentares individuais). Até 2019 o "
            "denominador era a RCL sem ajuste; para não misturar definições, a série começa no "
            "exercício de 2020. O limite para os estados é 200% (Resolução do Senado Federal nº "
            "40/2001). Pode ser negativo quando a DCL é negativa. Variações são expressas em "
            "pontos percentuais (p.p.)."
        ),
        "version": "MDF/STN; RGF Anexo 2, desde 2020",
    },
    {
        "code": "STATE_PERSONNEL_EXEC",
        "name": "Despesa total com pessoal do Poder Executivo estadual - últimos 12 meses",
        "short_name": "Despesa com pessoal (Executivo)",
        "description": (
            "Despesa total com pessoal do Poder Executivo do estado, para fins da LRF, somada nos "
            "12 meses encerrados no quadrimestre de referência."
        ),
        "series": "RGF-Anexo 01 · DespesaComPessoalTotal",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "four_monthly",
        "methodology": (
            "Despesa total com pessoal (LRF, arts. 18 e 19), como publicada no Anexo 1 do RGF do "
            "Poder Executivo: linha DespesaComPessoalTotal, coluna 'Valor'. Cada observação soma "
            "os 12 meses encerrados no quadrimestre de referência. " + EXECUTIVE_ONLY + " "
            "No 3º quadrimestre inclui as despesas inscritas em restos a pagar não processados, "
            "como determina o demonstrativo. " + NOMINAL_VALUES + " Série a partir do exercício "
            "de 2018."
        ),
        "version": "MDF/STN; RGF Anexo 1 (Executivo), desde 2018",
    },
    {
        "code": "STATE_PERSONNEL_EXEC_RCL",
        "name": "Despesa total com pessoal do Poder Executivo estadual sobre a RCL ajustada (%)",
        "short_name": "Pessoal do Executivo / RCL",
        "description": (
            "Despesa total com pessoal do Poder Executivo como percentual da receita corrente "
            "líquida ajustada para o cálculo dos limites de pessoal, como publicada pelo estado."
        ),
        "series": "RGF-Anexo 01 · DespesaComPessoalTotal (%)",
        "unit": "% da RCL ajustada",
        "change_unit": "p.p.",
        "frequency": "four_monthly",
        "methodology": (
            "Percentual publicado no Anexo 1 do RGF do Poder Executivo (linha "
            "DespesaComPessoalTotal, coluna '% sobre a RCL Ajustada'), sem recálculo pelo Atlas: "
            "despesa com pessoal e RCL ajustada referem-se aos mesmos 12 meses encerrados no "
            "quadrimestre. A composição dos ajustes da RCL para pessoal é definida pela "
            "legislação e mudou ao longo dos anos. O limite máximo do Executivo estadual é, em "
            "regra, 49% da RCL (LRF, art. 20, II, c), mas pode diferir conforme a repartição "
            "entre os Poderes do estado. " + EXECUTIVE_ONLY + " Variações são expressas em pontos "
            "percentuais (p.p.). Série a partir do exercício de 2018."
        ),
        "version": "MDF/STN; RGF Anexo 1 (Executivo), desde 2018",
    },
    {
        "code": "STATE_PRIMARY_RESULT",
        "name": "Resultado primário dos estados, acima da linha, sem RPPS - acumulado no ano",
        "short_name": "Resultado primário",
        "description": (
            "Receitas primárias menos despesas primárias pagas do estado, sem o regime próprio de "
            "previdência, acumuladas no ano até o bimestre. Positivo indica superávit; negativo, "
            "déficit."
        ),
        "series": "RREO-Anexo 06 · ResultadoPrimarioSemRPPSAcimaDaLinha",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "bimonthly",
        "methodology": (
            "Resultado primário pela metodologia 'acima da linha' (receitas primárias menos "
            "despesas primárias pagas, inclusive restos a pagar pagos), sem as receitas e "
            "despesas do regime próprio de previdência (RPPS), como publicado no Anexo 6 do RREO: "
            "linha ResultadoPrimarioSemRPPSAcimaDaLinha, coluna 'VALOR'. "
            + ACCUMULATED_IN_YEAR
            + " Valor positivo indica superávit e negativo, déficit. A série começa no exercício "
            "de 2023, quando a 13ª edição do Manual de Demonstrativos Fiscais separou o RPPS; os "
            "resultados de anos anteriores seguem outro conceito e não são emendados a esta "
            "série. " + NOMINAL_VALUES
        ),
        "version": "MDF 13ª ed.; RREO Anexo 6, desde 2023",
    },
    {
        "code": "STATE_NOMINAL_RESULT",
        "name": "Resultado nominal dos estados, acima da linha, sem RPPS - acumulado no ano",
        "short_name": "Resultado nominal",
        "description": (
            "Resultado primário sem RPPS somado aos juros, encargos e variações monetárias "
            "ativos e deduzido dos passivos, acumulado no ano até o bimestre. Negativo indica "
            "déficit nominal."
        ),
        "series": "RREO-Anexo 06 · ResultadoNominalAcimaDaLinhaSemRPPS",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "bimonthly",
        "methodology": (
            "Resultado nominal pela metodologia 'acima da linha', como publicado no Anexo 6 do "
            "RREO: linha ResultadoNominalAcimaDaLinhaSemRPPS, coluna 'VALOR'. É o resultado "
            "primário sem RPPS somado aos juros, encargos e variações monetárias ativos e "
            "deduzido dos passivos (exceto RPPS). " + ACCUMULATED_IN_YEAR + " Valor negativo "
            "indica déficit nominal (necessidade de financiamento). A série começa no exercício "
            "de 2023 (13ª edição do Manual de Demonstrativos Fiscais). " + NOMINAL_VALUES
        ),
        "version": "MDF 13ª ed.; RREO Anexo 6, desde 2023",
    },
    {
        "code": "STATE_INVESTMENTS",
        "name": "Investimentos liquidados dos estados - acumulado no ano",
        "short_name": "Investimentos",
        "description": (
            "Despesas com investimentos (obras, instalações, equipamentos e material permanente) "
            "liquidadas pelo estado, acumuladas no ano até o bimestre."
        ),
        "series": "RREO-Anexo 01 · Investimentos",
        "unit": BRL,
        "change_unit": BRL,
        "frequency": "bimonthly",
        "methodology": (
            "Despesas do grupo de natureza 4 (investimentos) liquidadas, exceto operações "
            "intraorçamentárias, como publicadas no Anexo 1 do RREO: linha Investimentos, coluna "
            "'DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)'. Liquidação é o reconhecimento de que a "
            "obra ou o bem foi entregue; não são despesas apenas empenhadas (compromissadas) nem "
            "pagas. " + ACCUMULATED_IN_YEAR + " No fim do exercício, investimentos empenhados e "
            "não liquidados são inscritos em restos a pagar não processados e não entram neste "
            "valor. " + NOMINAL_VALUES + " Série a partir do exercício de 2018."
        ),
        "version": "MDF/STN; RREO Anexo 1, desde 2018",
    },
]

FIRST_EXERCISE = {"STATE_DCL_RCL": 2020, "STATE_PRIMARY_RESULT": 2023, "STATE_NOMINAL_RESULT": 2023}


def upgrade() -> None:
    op.drop_constraint(op.f("ck_indicators_frequency"), "indicators", type_="check")
    op.create_check_constraint(op.f("ck_indicators_frequency"), "indicators", NEW_FREQUENCIES)
    conn = op.get_bind()
    for indicator in INDICATORS:
        first = FIRST_EXERCISE.get(indicator["code"], 2018)
        conn.execute(
            sa.text(
                """
                INSERT INTO indicators (
                    code, name, short_name, description, source_id, source_series_code,
                    source_url, unit, change_unit, frequency, geographic_level, methodology,
                    methodology_version, first_available_date
                )
                SELECT :code, :name, :short_name, :description, id, :series, :source_url,
                       :unit, :change_unit, :frequency, 'state', :methodology, :version,
                       make_date(:first, 1, 1)
                FROM data_sources WHERE acronym = 'SICONFI'
                """
            ),
            {**indicator, "source_url": SOURCE_URL, "first": first},
        )


def downgrade() -> None:
    conn = op.get_bind()
    codes = {"codes": [i["code"] for i in INDICATORS]}
    conn.execute(
        sa.text(
            """
            DELETE FROM observation_revisions WHERE observation_id IN (
                SELECT o.id FROM observations o JOIN indicators i ON i.id = o.indicator_id
                WHERE i.code = ANY(:codes))
            """
        ),
        codes,
    )
    for table in ("observations", "ingestion_runs"):
        conn.execute(
            sa.text(
                f"DELETE FROM {table} WHERE indicator_id IN "
                "(SELECT id FROM indicators WHERE code = ANY(:codes))"
            ),
            codes,
        )
    conn.execute(sa.text("DELETE FROM indicators WHERE code = ANY(:codes)"), codes)
    op.drop_constraint(op.f("ck_indicators_frequency"), "indicators", type_="check")
    op.create_check_constraint(op.f("ck_indicators_frequency"), "indicators", OLD_FREQUENCIES)
