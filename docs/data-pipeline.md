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
uv run python -m app.ingestion.cli ingest-boundaries             # malha das 27 UFs (IBGE, IBGE_MESH_YEAR)
uv run python -m app.ingestion.cli ingest-boundaries --year 2021 # outra edição da malha
uv run python -m app.ingestion.cli ingest-siconfi --report RREO --annex "RREO-Anexo 03" \
    --state SP --state RJ --year 2024                            # anexo do SICONFI (S3), incremental
uv run python -m app.ingestion.cli ingest-siconfi --report RGF --annex "RGF-Anexo 02" \
    --state SP --year 2024 --period 3 --refresh                  # força a recoleta do período
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

## Conector IBGE/Malhas — geometrias das UFs (S2)

```
GET https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json
    &intrarregiao=UF&qualidade=minima&periodo={edição}
```

Código: `app/integrations/ibge/malhas.py` (conector) e `app/ingestion/boundaries.py` (gravação).
A edição vem de `--year` ou de `IBGE_MESH_YEAR` (padrão `2022`). As malhas mudam no máximo uma vez
por ano, por isso a coleta é manual (fora do agendador). Comportamentos observados (21/10/2026):

| Situação | Resposta do IBGE | Tratamento |
|---|---|---|
| Sucesso | `200` GeoJSON `FeatureCollection`, 27 feições com `properties.codarea` (código da UF) e `Polygon`/`MultiPolygon` | Validação de cada feição: código numérico único, anéis fechados com ≥ 4 posições, coordenadas finitas dentro do Brasil (incl. ilhas oceânicas) |
| Edição inexistente (2023 em diante e anos anteriores a 2019, ex.: 2000, 2010, 2013, 2018) | `500` `{"statusCode":500,"message":"Internal server error"}` | Indistinguível de uma falha temporária: retry; depois das tentativas, `MalhasUnavailableError` com o aviso de que o IBGE responde 500 para edições não publicadas |
| Edições disponíveis nesta consulta | 2019, 2020, 2021 e 2022 (conferido em 21/10/2026) | — |
| Sem `periodo` | Edição 2022 (a mais recente) | O conector sempre envia `periodo`, para a edição gravada ser explícita |
| `429`/`5xx`/erro de rede/`200` não JSON | — | Retry com backoff exponencial; rate limit `IBGE_MIN_REQUEST_INTERVAL_SECONDS` |
| Outros códigos HTTP | — | Erro permanente, sem retry |

Regras de gravação:

- Os códigos recebidos precisam casar **1:1** com as 27 UFs de `geographic_units`; faltando ou sobrando
  um código, nada é gravado e a execução fica `failed` em `ingestion_runs` (sem `indicator_id`,
  `metadata_json.dataset = "state_boundaries"`). Uma falha nunca apaga a malha já armazenada.
- Idempotência: unicidade (unidade, edição, qualidade). Recoletar a mesma edição só reescreve a
  geometria cujo hash SHA-256 (JSON canônico) mudou; os códigos alterados ficam em
  `metadata_json.updated_codes`, com o hash do payload bruto em `metadata_json.content_hash`.
- Edições diferentes convivem (versionamento por `mesh_year`).

Simplificação e quantização: usa-se a malha **generalizada pelo próprio IBGE** (`qualidade=minima`,
~98 KB para as 27 UFs; `intermediaria` ~250 KB, `maxima` ~1 MB), sem simplificação adicional. As
coordenadas são quantizadas em 4 casas decimais (~11 m), o que não altera a edição 2022 (o IBGE já as
entrega assim). A API comprime com gzip (~28 KB). A malha generalizada **omite as pequenas ilhas
oceânicas** (Fernando de Noronha, Trindade e Martim Vaz; longitudes de -73,99 a -34,80): o mapa não
deve sugerir que elas estejam representadas.

Verificação real (21/10/2026): coleta da edição 2022 com 27 feições inseridas; reexecução `inserted 0,
updated 0, unchanged 27`; as 27 geometrias servidas por `/api/v1/geographies/states/boundaries` são
idênticas às da consulta oficial, e os 27 códigos casam com os de `/api/v1/geographies?level=state`.

## Conector SICONFI — relatórios fiscais dos estados (S3)

`app/integrations/tesouro/siconfi.py` consulta a API de dados abertos do SICONFI (Tesouro Nacional,
[documentação](https://apidatalake.tesouro.gov.br/docs/siconfi/)); `app/ingestion/siconfi.py` grava os
anexos em `fiscal_reports` (um registro por ente × relatório × exercício × período × anexo × esfera ×
poder) e `fiscal_report_rows` (cada valor publicado, `NUMERIC(24,8)`). É a **camada bruta**: os valores
ficam exatamente como publicados; os indicadores fiscais (RCL, DCL, DCL/RCL etc.) serão derivados dela
na S4, com validação do economist. A coleta é manual (fora do agendador) até a S4 definir quais anexos
alimentam indicadores. Decisões em [ADR 0009](adr/0009-conector-siconfi-camada-bruta.md).

Endpoints usados:

| Endpoint | Parâmetros | Uso |
|---|---|---|
| `GET /tt/rreo` | `an_exercicio`, `nr_periodo` (bimestre 1–6), `co_tipo_demonstrativo=RREO`, `no_anexo` (ex.: `RREO-Anexo 03`), `co_esfera` (`E` = estados e DF; a API aceita também `M`, `U` e `C` = consórcio; conferido: as linhas do DF, `id_ente=53`, voltam com `esfera` `E`), `id_ente` (código IBGE da UF) | Anexo do RREO, consolidado do ente (sem poder) |
| `GET /tt/rgf` | os mesmos, mais `in_periodicidade` (`Q` quadrimestral; `S`, semestral, é o *RGF Simplificado* de municípios com menos de 50 mil habitantes, LRF art. 63, fora do escopo e recusado pelo conector) e `co_poder` (`E` Executivo, `L` Legislativo, `J` Judiciário, `M` Ministério Público, `D` Defensoria Pública) | Anexo do RGF de um poder (padrão: Executivo) |
| `GET /tt/extrato_entregas` | `id_ente`, `an_referencia` | Entregas e retificações do ente no ano (`data_status`, `status_relatorio`: `HO` homologado, `RE` retificado) |

Comportamento observado (21/10/2026):

| Situação | Resposta do SICONFI | Tratamento |
|---|---|---|
| Sucesso | `200` página ORDS: `items`, `hasMore`, `limit` (5000), `offset`, `count`, `links` | Validação de cada linha contra o pedido (exercício, período, periodicidade, anexo, esfera, poder ou `demonstrativo`, `cod_ibge`); `valor` lido do texto JSON direto para `Decimal` |
| Mais de uma página | `hasMore: true` | Novas páginas com `offset` += linhas recebidas (`limit=5000`); página vazia com `hasMore`, `offset` diferente do pedido ou mais de 50 páginas são erro. Um anexo de uma UF cabe numa página (o maior visto: RREO-Anexo 01 do RJ, 671 linhas) |
| Filtro ausente ou inexistente (ente, anexo, período sem dados) | `200` com `items: []` | Não é erro: "ainda não disponível". Nada é gravado e o período é tentado de novo na próxima coleta (`not_available`) |
| Linha repetida (mesmo `rotulo`, `coluna`, `cod_conta`, `conta`) | não observada | `SiconfiPayloadError`: o anexo inteiro é recusado (protege contra paginação instável) |
| `429`/`5xx`/erro de rede/`200` não JSON | — | Retry com backoff exponencial (`HTTP_MAX_RETRIES`, `HTTP_BACKOFF_BASE_SECONDS`) |
| Outros códigos HTTP | — | Erro permanente, sem retry |

**Limite de taxa.** A documentação oficial limita a API a 1 requisição por segundo. O cliente espaça o
início de duas requisições em pelo menos `SICONFI_MIN_REQUEST_INTERVAL_SECONDS` (padrão 1,1 s; a
configuração recusa valores abaixo de 1,0), inclusive entre tentativas e páginas; um teste com relógio
simulado comprova o espaçamento.

**Coleta incremental.** Para cada UF e exercício, uma requisição ao `extrato_entregas`; para cada
período pedido:

1. sem entrega listada → `not_delivered` (nenhuma requisição ao relatório);
2. já armazenado com `delivered_at` ≥ a entrega mais recente listada → `up_to_date` (nenhuma requisição);
3. caso contrário (ou com `--refresh`) → coleta o anexo: `inserted` (novo), `unchanged` (mesmo
   `content_hash`) ou `updated` (retificação).

A entrega mais recente de um período é o maior `data_status` entre **todos** os órgãos que entregaram
aquele relatório (no RGF cada poder entrega o seu); isso pode recoletar um anexo sem mudança, o que é
inofensivo, mas nunca deixa de ver uma retificação. Se o data lake ainda servir a versão anterior quando a
nova entrega já aparece no extrato, a coleta grava o conteúdo antigo com a data nova; `--refresh` corrige.

**Idempotência e revisões.** Unicidade (UF, relatório, exercício, periodicidade, período, anexo, esfera,
poder; `NULLS NOT DISTINCT`, pois o RREO não tem poder) e, por linha, (`rotulo`, `coluna`, `cod_conta`,
`conta`). `content_hash` é o SHA-256 das linhas canônicas (ordenadas, valores sem zeros à direita),
independente da paginação. Numa retificação, as linhas alteradas, novas e removidas são aplicadas e
cada mudança fica em `ingestion_runs.metadata_json.revisions` (linha, valor anterior, valor novo e hash
anterior; até 1000 por execução, com o total em `revision_count`). Cada anexo é gravado na própria
transação: uma falha preserva os anexos já coletados e a execução fica `failed`, com os resultados até
ali em `metadata_json.reports`.

Verificação real (21/10/2026): RREO-Anexo 03 (bimestres 1–6) e RGF-Anexo 02 (quadrimestres 1–3,
Executivo) de 2024 para SP e RJ: 18 anexos, 5.452 linhas, 22 requisições, sempre ≤ 1/s; RREO de SP de
2026: bimestres 1–4 gravados, 5–6 `not_delivered`. Reexecução: só as 2 requisições ao extrato, tudo
`up_to_date`; com `--refresh`, 561 linhas `unchanged`. Três anexos conferidos linha a linha contra uma
consulta independente à API oficial (SP RGF-Anexo 02 3º quadrimestre: 124 linhas; RJ RREO-Anexo 03 6º
bimestre: 401; RJ RGF-Anexo 02 1º quadrimestre: 62): idênticos. Exemplo: dívida consolidada líquida (DCL) do Estado de São Paulo, saldo ao fim do 3º
quadrimestre de 2024 (31/12/2024), RGF-Anexo 02 publicado pelo Poder Executivo (`cod_conta`
`DividaConsolidadaLiquida`, coluna "Até o 3º Quadrimestre") = R$ 317.655.576.689,71, em valores
correntes. O demonstrativo da DCL é publicado só pelo Executivo, mas abrange todos os Poderes do ente
(MDF/STN).

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
