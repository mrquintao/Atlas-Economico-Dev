# Pipeline de ingestão

## Execução

```bash
cd services/api
uv run python -m app.ingestion.cli ingest SELIC_TARGET           # incremental
uv run python -m app.ingestion.cli ingest SELIC_TARGET --full    # todo o histórico oficial
uv run python -m app.ingestion.cli ingest SELIC_TARGET --start 2020-01-01 --end 2020-12-31
uv run python -m app.ingestion.cli ingest DBGG_GDP               # mensal: sempre a série inteira
uv run python -m app.ingestion.cli ingest IPCA_12M               # IBGE/SIDRA: sempre a série inteira
uv run python -m app.ingestion.cli ingest --all                  # todos os indicadores do catálogo
```

A CLI escolhe o conector pela fonte do indicador (`data_sources.acronym`): `BCB` → SGS
(`app/integrations/bcb/sgs.py`), `IBGE` → SIDRA (`app/integrations/ibge/sidra.py`). Idempotência,
revisões e `ingestion_runs` são os mesmos para todas as fontes (`app/ingestion/series_ingestion.py`).

A CLI imprime um resumo JSON por indicador (stdout: `indicator`, `status`, `run_id`, `error`,
`summary`); logs estruturados em JSON vão para stderr. Código de saída: `0` quando todas as coletas
pedidas terminam com sucesso, `1` quando alguma falha (ou o código do indicador não existe), `2` para
argumentos inválidos (ex.: `--start` posterior a `--end`).

## Coleta automática

Sem filas ou orquestradores, de propósito (`PROJECT_SPEC.md` §7):

- **Docker Compose:** serviço opcional `scheduler` (perfil `scheduler`, `app/ingestion/scheduler.py`).
  Um processo de longa duração espera o próximo horário de `INGEST_SCHEDULE` (`HH:MM`, vários
  separados por vírgula, no fuso `America/Sao_Paulo`; padrão `06:00`) e executa a mesma coleta de
  `ingest --all`. `INGEST_ON_START=true` também coleta ao iniciar. Configuração inválida encerra o
  serviço com código 2; `python -m app.ingestion.scheduler --check` valida a configuração e mostra
  a próxima execução, e também confere a conexão com o banco migrado (catálogo não vazio). Uma coleta
que falha é registrada e não derruba o agendador; ao receber `SIGTERM`, o agendador termina o
indicador em andamento e não inicia os seguintes.
- **Fora do Docker:** `scripts/ingest.sh` (`ingest --all`) num cron do sistema.

Garantias de cada execução em lote (`app/ingestion/batch.py`):

- cada indicador é coletado de forma independente e atômica: a falha de um não impede os demais;
- toda tentativa que chega a consultar o catálogo gera uma linha em `ingestion_runs` — inclusive
  falhas anteriores à requisição (intervalo inválido, fonte sem conector), com `status = failed` e a
  mensagem em `error_message`. Ficam só nos logs: banco indisponível, catálogo sem a unidade
  nacional e falha ao criar o conector;
- runs deixados em `running` por um processo interrompido (ex.: `SIGKILL`) são marcados como `failed`
  ("Interrupted…") no início do lote seguinte, quando têm mais de 1 hora;
- uma resposta **vazia** para um intervalo que já tem observações gravadas é falha (`IngestionError`),
  não sucesso: os dados gravados são mantidos e a "última coleta" não avança;
- `--start` posterior a `--end` ou no futuro é rejeitado pela CLI antes de qualquer coleta;
- os conectores são abertos uma vez por fonte e respeitam o intervalo mínimo entre requisições;
- uma coleta que não recebe nenhum registro num intervalo ainda sem dados gravados termina com
  sucesso, mas gera o aviso `ingestion_received_no_records` no log para conferência.

Monitoramento: os logs (`docker compose logs scheduler`: `scheduler_waiting`, `batch_finished`,
`batch_indicator_failed`, `scheduled_collection_finished`), a tabela `ingestion_runs` e o campo
`last_run` de `GET /api/v1/indicators` (ver [api.md](api.md)), exibido no painel de metodologia
quando a última tentativa falhou ou está em andamento.

Parar o serviço durante uma coleta: o Compose concede 2 minutos (`stop_grace_period`) para concluir o
indicador em andamento; se o processo for interrompido à força, o run fica `running` até o lote
seguinte o marcar como interrompido, e os dados gravados permanecem consistentes (cada indicador é
gravado numa única transação).

Limitações conhecidas: um horário perdido (contêiner parado) não é recuperado automaticamente
(use `INGEST_ON_START=true` ou `ingest --all`); não há trava contra duas coletas simultâneas do mesmo
indicador — evite rodar `ingest` manualmente enquanto o agendador coleta.

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
| Caminho inexistente (URL base errada) | `404` JSON `{"error": "endpoint not found!"}` | Erro, sem retry (antes da M4 era tratado como janela vazia e a falha passava por sucesso) |
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

Uma única requisição traz a série inteira (~550 meses, ~1 s). Rate limit próprio:
`IBGE_MIN_REQUEST_INTERVAL_SECONDS` (0,5 s). O cabeçalho é validado (formato de códigos, nível Brasil,
período mensal), assim como a variável, a unidade e o território de cada linha; linhas sem valor
chegam com unidade vazia (`"MC": ""`) e são descartadas antes da checagem de unidade.

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
