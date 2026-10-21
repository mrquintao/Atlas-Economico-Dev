# ADR 0010 — Indicadores fiscais estaduais derivados do SICONFI

**Status:** aceito (2026-10-21), issue #14 (S4). Mapeamento validado pelo agente `economist` contra a
API oficial; parecer e amostras em [`../state-fiscal-indicators.md`](../state-fiscal-indicators.md).

## Contexto

A S3 ([ADR 0009](0009-conector-siconfi-camada-bruta.md)) grava os anexos do RREO e do RGF tal como
publicados (`fiscal_reports`/`fiscal_report_rows`). A S4 precisa transformar linhas desses anexos em
séries do catálogo (`indicators`/`observations`, nível `state`), sem misturar conceitos (§16 da spec) e
mantendo a rastreabilidade de cada número até a linha oficial.

## Decisões

1. **Um indicador = uma linha publicada.** Cada indicador é identificado por relatório, anexo, poder,
   `cod_conta` e coluna, com igualdade exata (vários códigos são prefixos de outros, ex.:
   `DividaConsolidada` e `DividaConsolidadaLiquida`). Nada é calculado a partir de várias linhas: os
   percentuais (DCL/RCL, pessoal/RCL) são os publicados nos demonstrativos. O `rotulo` não é usado
   ("Padrão" desde 2017, nulo antes). O mapeamento vive em `app/ingestion/fiscal_catalog.py`, com faixa
   de exercícios por seletor; um exercício fora de toda faixa não tem observação.
2. **Derivação separada da coleta.** `derive-fiscal` lê só a camada bruta e pode ser repetida sem
   chamar o SICONFI; `--collect` coleta antes os anexos necessários (`ingest_siconfi_reports`).
   Os indicadores do SICONFI não têm conector de séries: `ingest --all` e o agendador os ignoram, e
   `ingest STATE_*` é recusado antes de registrar execução.
3. **Resultados da derivação por período:** linha encontrada → `inserted`/`updated`/`unchanged`
   (mudança de valor vai para `observation_revisions`); linha ausente → `row_missing` (lacuna; valor já
   armazenado é mantido e relatado, como nas séries nacionais); mais de uma linha → `ambiguous`, a
   execução falha e nada é gravado, porque o mapeamento deixou de identificar o valor.
4. **Período de referência (ADR 0005):** bimestre do RREO (`bimonthly`) ou quadrimestre do RGF
   (`four_monthly`), com `reference_date = period_start` (1º dia) e `period_end` no último dia. A
   janela de acumulação (12 meses, no ano ou saldo) é metadado do indicador. No RGF, a coluna do
   período *n* é lida só do relatório do período *n* (o 3º quadrimestre republica os anteriores).
5. **Rastreabilidade:** `observations.metadata_json` guarda o id do anexo e da linha, `cod_conta`,
   coluna, conta e URL da consulta; `published_at` é a data da entrega no `extrato_entregas`.
6. **Escolhas do economist (definições):**
   - RCL da LRF (não as ajustadas), a partir de 2018;
   - DC e DCL do Anexo 2 do RGF do Executivo (estado inteiro), a partir de 2018; DCL pode ser negativa;
   - DCL/RCL a partir de **2020**, quando o denominador publicado passou a ser a RCL ajustada para
     endividamento (até 2019 era a RCL; não se emendam as duas definições);
   - despesa com pessoal **só do Poder Executivo**, em R$ e em % da RCL ajustada (relatórios de
     poderes diferentes não são somados);
   - resultados primário e nominal "acima da linha", **sem RPPS**, só a partir de **2023** (13ª edição
     do MDF); antes disso a linha tem outro conceito;
   - investimentos liquidados (GND 4), exceto intraorçamentários, acumulados no ano.

## Consequências

- Novos valores de frequência: `bimonthly` e `four_monthly` (migração 0009).
- Fluxos acumulados no ano (`year_to_date` no mapeamento: resultados primário e nominal e
  investimentos) recomeçam em janeiro; por isso `GET /indicators/{code}/observations` não serve
  `stats` (variação, mínimo e máximo) para eles, que comparariam bimestres de naturezas diferentes.
- "Última coleta" (`last_collected_at`) de um indicador derivado é a data de coleta mais recente dos
  anexos por trás das observações armazenadas (`observations.collected_at`), não a data da derivação.
- `ingest --all` e o agendador ignoram explicitamente a fonte SICONFI (`DERIVED_SOURCES`); outra fonte
  sem conector continua gerando execução com falha, para não sumir em silêncio.
- Limitação conhecida: se uma retificação remover a linha de um período já derivado, a observação
  é mantida com o valor anterior (como nas séries nacionais), o período aparece como `row_missing`
  em cada derivação e `metadata_json.fiscal_report_row_id` passa a apontar para uma linha inexistente.
- Pessoal/RCL desde 2018 e DCL/RCL só desde 2020: no Anexo 1 do RGF o denominador já é a "RCL
  ajustada" para pessoal em todo o período (coluna `% sobre a RCL Ajustada` desde 2017); as mudanças
  nos itens deduzidos decorrem da legislação aplicável ao limite e não mudam o conceito do indicador
  (percentual legal publicado). No Anexo 2, o denominador mudou de conceito em 2020 (RCL → RCL
  ajustada para endividamento), por isso a série começa nesse ano.
- No catálogo (`GET /indicators`), o período armazenado de um indicador estadual considera todas as
  UFs; `GET /indicators/{code}/observations?geography=UF` já serve cada UF.
- Fora do escopo agora: resultados de 2018–2022 (série própria, se vier), resultados com RPPS ou
  abaixo da linha, pessoal dos demais poderes e total do ente, RCL ajustada isolada, empenhado/pago,
  passivo atuarial, metas da LDO, valores per capita e em % do PIB estadual.
- Pendências herdadas da S3: trava entre processos antes de pôr o SICONFI no agendador; recoletar
  com `--refresh` os anexos usados se houver retificação tardia (issue #14, comentário da S3).
