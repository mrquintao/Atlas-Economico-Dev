# Pipeline de ingestão

## Execução

```bash
cd services/api
uv run python -m app.ingestion.cli ingest SELIC_TARGET           # incremental
uv run python -m app.ingestion.cli ingest SELIC_TARGET --full    # todo o histórico oficial
uv run python -m app.ingestion.cli ingest SELIC_TARGET --start 2020-01-01 --end 2020-12-31
uv run python -m app.ingestion.cli ingest DBGG_GDP               # mensal: sempre a série inteira
uv run python -m app.ingestion.cli ingest IPCA_12M               # IBGE/SIDRA: sempre a série inteira
```

A CLI escolhe o conector pela fonte do indicador (`data_sources.acronym`): `BCB` → SGS
(`app/integrations/bcb/sgs.py`), `IBGE` → SIDRA (`app/integrations/ibge/sidra.py`). Idempotência,
revisões e `ingestion_runs` são os mesmos para todas as fontes (`app/ingestion/series_ingestion.py`).

A CLI imprime um resumo JSON (stdout); logs estruturados em JSON vão para stderr.
Agendamento simples: `scripts/ingest.sh` via cron (sem filas ou orquestradores, de propósito).

## Etapas

1. **Intervalo:** `--start/--end` explícitos; senão incremental conforme a frequência — séries **diárias**
   a partir de (última data armazenada − 90 dias); séries **mensais** sempre desde `first_available_date`
   (revisões do PIB podem alterar anos anteriores e a série inteira cabe numa requisição). Sem dados ou
   com `--full`, desde `first_available_date`. O fim nunca passa da data da coleta **no horário de Brasília**.
2. **Registro da execução** em `ingestion_runs` (status `running`), commitado antes da coleta.
3. **Requisições ao SGS** em janelas (séries diárias: padrão 1 ano; limite oficial 10 anos). Séries
   mensais em uma única requisição.
4. **Validação:** content-type JSON, array de objetos `{data, valor}`, datas `dd/mm/aaaa`, números decimais
   finitos, sem datas duplicadas, todas as datas dentro da janela pedida.
5. **Normalização:** datas → `DATE`, valores → `Decimal`; nulos descartados (contados); datas futuras descartadas.
   Período de referência: diário = o próprio dia; mensal = dia 1 até o último dia do mês (datas mensais
   fora do dia 1 são rejeitadas).
6. **Comparação com o banco:** novos → `INSERT … ON CONFLICT DO NOTHING`; alterados → `UPDATE` + linha em
   `observation_revisions`; iguais → contados como `unchanged`.
7. **Transação única:** se qualquer janela falhar, nada é gravado; a execução fica `failed` com a mensagem de erro.
8. **Finalização:** contagens, janelas consultadas (URL, nº de registros, SHA-256 do payload bruto).

## Conector BCB/SGS — endpoint efetivamente usado

```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa
```

Comportamentos observados (21/10/2026) e tratamento:

| Situação | Resposta do BCB | Tratamento |
|---|---|---|
| Sucesso | `200` JSON `[{"data":"01/01/2024","valor":"11.75"}, …]` | Parsing e validação |
| Janela sem dados | `404` JSON `{"erro": {… "Value(s) not found"}}` | Janela vazia (não é erro) |
| Janela > 10 anos (diária) | `406` JSON `{"error": "O sistema aceita uma janela … 10 anos …"}` | Erro permanente, sem retry |
| Falha intermitente do gateway | `400` **HTML** “Requisição inválida” | Retry com backoff |
| Lentidão em janelas grandes | 5 e 10 anos levam ~30 s e frequentemente estouram o timeout | Janela padrão de 1 ano (~1 s) |
| `429`/`5xx`/erro de rede/timeout | — | Retry com backoff exponencial (1 s, 2 s, 4 s, 8 s) |

Rate limit: intervalo mínimo de 0,5 s entre requisições (`BCB_MIN_REQUEST_INTERVAL_SECONDS`).

## Conector IBGE/SIDRA — endpoint efetivamente usado

```
GET https://apisidra.ibge.gov.br/values/t/{tabela}/n1/all/v/{variável}/p/{AAAAMM}-{AAAAMM}/f/c
```

`source_series_code` guarda `tabela/variável` (ex.: `1737/2265`); `source_reference` das observações
é `sidra.t1737.v2265`. Comportamentos observados (21/10/2026) e tratamento:

| Situação | Resposta do SIDRA | Tratamento |
|---|---|---|
| Sucesso | `200` JSON: 1º item = cabeçalho (`"V": "Valor"`), demais `{"MC","V","D2C","D3C",…}` | Validação do cabeçalho, da variável (`D2C`), da unidade (`MC = 2`, %) e do mês (`D3C` = `AAAAMM`) |
| Valor inexistente | `"V": "..."` (ou `..`, `-`, `X`) | Ausência: descartado e contado, nunca zero |
| Período sem dados (ex.: meses futuros) | `200` só com o cabeçalho | Janela vazia |
| Parâmetro inválido | `400` | Erro permanente, sem retry |
| `429`/`5xx`/erro de rede/timeout/`200` não JSON | — | Retry com backoff exponencial |

Uma única requisição traz a série inteira (~550 meses, ~1 s).

## Verificação real (20–21/10/2026)

- Coleta completa: 28 janelas de 1 ano, 05/03/1999 até a data da coleta; uma linha por dia corrido,
  sem duplicatas; amostras conferidas contra a API oficial pelos agentes `economist` e `qa-auditor`
  (ver [catálogo](indicators.md)).
- Reexecução incremental: `received 91, inserted 0, updated 0, unchanged 91` (idempotente).
- Problemas encontrados e corrigidos durante a validação:
  - `rowcount` de INSERT multi-linha vinha `-1` no psycopg → a contagem passou a usar `RETURNING`.
  - A "data da coleta" era calculada em UTC: uma coleta às 21h de Brasília gravava o dia seguinte
    (pré-publicado pelo BCB). Agora usa o fuso `America/Sao_Paulo` (`app/core/clock.py`).
  - Janelas de 10 anos estouravam o timeout → janela padrão de 1 ano.
- Datas armazenadas que a fonte deixa de retornar não são apagadas: são listadas em
  `metadata_json.missing_from_source` e geram aviso no log.

### DBGG_GDP (21/10/2026)

- Coleta real: 1 requisição, **237 observações** de dez/2006 a ago/2026 (sem lacunas); reexecução:
  `inserted 0, updated 0, unchanged 237`. Amostras conferidas: ver [catálogo](indicators.md).

### IPCA_12M (21/10/2026)

- Coleta real: 1 requisição, **550 observações** de dez/1980 a set/2026 (sem lacunas a partir de
  dez/1980); reexecução: `inserted 0, updated 0, unchanged 550`. Amostras e recálculo independente
  a partir da variação mensal: ver [catálogo](indicators.md).
