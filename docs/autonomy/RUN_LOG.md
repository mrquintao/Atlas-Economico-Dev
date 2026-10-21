# Registro de execuções

Entradas curtas, da mais recente para a mais antiga: o que foi entregue, o que foi validado, as falhas e
como foram corrigidas, e as decisões relevantes. Os detalhes ficam nos PRs, nas issues e nos ADRs.

## 2026-10-21 — M6 concluída: testes E2E com Playwright (issue #8, PR #35)

- Fixture SINTÉTICA `services/api/tests/fixtures/e2e_seed.py`: séries determinísticas, cada linha
  identificada. Três travas: `ATLAS_E2E_SEED=1`, nome do banco com `e2e`/`test` e banco sem
  observações nem execuções de coleta. 8 pytest.
- `apps/web/e2e` (`@playwright/test` 1.63.0), 11 testes:
  - painel;
  - presets nos três gráficos;
  - cursor dia→mês e mês→último dia;
  - cursor oculto fora da série;
  - zoom sincronizado;
  - troca diária/mensal mantendo o zoom;
  - estado vazio e intervalo inválido;
  - páginas de catálogo;
  - console sem erros em todos.
  Os testes são caixa-preta: leem os tooltips HTML do ECharts e os nomes acessíveis.
- CI: job `E2E (Playwright)`, sem retries, no gate de merge. Sem Docker Compose (ADR 0008).
- Mutações em `chart-sync.ts` (`alignTime`, `syncZoom`, `afterOptionUpdate`, limite de extensão do
  cursor) são detectadas pelos testes correspondentes. 11/11 em 3 execuções locais seguidas e verde
  no CI em 3 commits consecutivos.
- qa-auditor: sem críticos/altos. Médio corrigido: a fixture podia gravar no banco `atlas` (dados
  reais) se ele estivesse vazio. Baixos corrigidos: espera do *throttle* do zoom, asserções completas
  dos presets, teste do cursor oculto, `pg_isready -d`, texto do ADR sobre `next start`.
- Incidente local: um `pgrep -f` casou com o próprio shell e encerrou servidores e o PostgreSQL de
  desenvolvimento; reiniciados sem perda (o banco `atlas` continua intacto).

## 2026-10-21 — M5 concluída: páginas "Metodologia" e "Fontes de dados" (issue #7, PR #34)

- Frontend: `/metodologia` lista todos os indicadores de `GET /indicators` e `/fontes` as fontes de
  `GET /sources` com os indicadores de cada uma. A navegação do cabeçalho marca a página atual com
  `aria-current`. `IndicatorMetadata` é compartilhado com o painel de cada gráfico, que ganhou link para
  a página; não há texto metodológico no frontend. Âncoras por código, com rolagem depois do
  carregamento. Estados de carregamento, erro e vazio. Nenhuma mudança na API ou no banco.
- qa-auditor: sem críticos. Alto corrigido: um hash malformado (`#%E0`) derrubava a página por causa de
  `decodeURIComponent`. Médio corrigido: `/fontes#ID` rolava antes de os indicadores carregarem.
  Baixos corrigidos: o texto sobre revisões, o rótulo do link e "SGS" repetido; os demais ficaram
  registrados na #7. As duas regressões têm testes que falham sem a correção.
- Ambiente: sessão nova, sem `/tmp/pgdata`. O PostgreSQL foi reinicializado e o banco `atlas` recebeu
  coleta real (`ingest --all`).

## 2026-10-21 — M4 concluída: coleta automática (issue #6, PR #33)

- `app/ingestion/batch.py` + CLI `ingest --all` (falha isolada por indicador, saída 1 se algum falhar,
  `2` para argumentos inválidos); `scheduler.py` (`INGEST_SCHEDULE` em Brasília, `INGEST_ON_START`,
  `--check` com conexão ao banco, SIGTERM para entre indicadores); serviço `scheduler` (perfil) e
  healthcheck da API no Compose; CI sobe o perfil com horário 12 h à frente; `tzdata` explícito.
- API: `last_run` (status, horários, só `error_type`); painel de metodologia avisa falha/andamento.
- Achado na validação real: um 404 do gateway do BCB (`{"error": "endpoint not found!"}`, URL errada)
  era tratado como janela vazia e a coleta saía como **sucesso** com 0 registros. Corrigido no conector.
- qa-auditor: sem críticos/altos. Médios corrigidos: runs órfãos em `running` (fechados após 1 h),
  resposta vazia para intervalo com dados gravados agora é falha, `--check` confere o banco, CLI rejeita
  intervalo inválido antes de gravar runs. Baixos corrigidos: `run_id` no relatório de falha, texto do
  painel sem coleta anterior, CI sem coleta real, documentação. Registrados (ADR 0007): horários
  perdidos, ausência de trava de concorrência.
- Ambiente: `/tmp/pgdata` recriado; dados reais recoletados no banco `atlas`.

## 2026-10-21 — M3 concluída: `GET /api/v1/dashboard/national` (issue #5, PR #32)

- Backend: `services/dashboard.py` (último valor e mesmo mês do ano anterior, reaproveitando
  `load_series`; série diária lida pelo último valor de cada mês), esquema `NationalDashboardOut` com
  `status` (`available`/`no_data`), `aggregation`, `latest` (com `partial`) e `change_12m` em `change_unit`;
  diferença calculada em `Decimal`. `Cache-Control: public, max-age=300`; 500 declarado no OpenAPI.
- Frontend: os três cartões usam uma única requisição (antes, uma série mensal completa por cartão);
  `latestFromMonthly` substituída por `latestFromDashboard`.
- Validação com dados reais (banco recriado: 10.093 dias de Selic, 237 meses de DBGG, 550 de IPCA):
  resposta idêntica ao cálculo antigo do cartão nos 3 indicadores (sem o ruído de float do JS) e
  conferida contra SGS 432, SGS 13762 e SIDRA 1737/2265.
- qa-auditor: sem críticos/altos. Corrigidos: mês parcial não sinalizado (novo `latest.partial`),
  comparação diária documentada, 500 declarado e testado, teste de equivalência com série longa,
  consulta repetida da geografia. Registrado: retry repetido por cartão em erro (baixo).
- Testes: 153 pytest, 53 vitest.

## 2026-10-21 — M2 concluída: IPCA 12 meses (issue #4, PR #30, merge `93decf8`)

- Conector `integrations/ibge/sidra.py` (tabela 1737, variável 2265, validada na API); ingestão genérica
  `ingestion/series_ingestion.py` com despacho por fonte na CLI; migração 0005 (fonte IBGE, `IPCA_12M`).
- Frontend: cartão do IPCA ("Referência: mês/ano", variação em p.p., fonte SIDRA) e terceiro gráfico
  sincronizado. Novo: quebra explícita da linha em períodos ausentes (antes eram ligados por cima).
- Coleta real: 550 meses (dez/1980–set/2026), reexecução `inserted 0, unchanged 550`; série inteira
  igual ao SIDRA; recálculo a partir da variação mensal com diferença ≤ 0,009 ponto desde 1996.
- qa-auditor: sem críticos. Corrigidos: fixture real do SIDRA (linhas `...` vêm com `"MC": ""`),
  descrição exagerada da verificação independente, docs/README/estado desatualizados, validação do
  cabeçalho (mensal, Brasil), duplicidade em linhas ausentes, rate limit próprio do IBGE, rótulo da
  fonte no painel, eixo vertical que cortaria valores negativos.
- Ambiente: a sessão não tinha `/tmp/pgdata`; PostgreSQL 16 recriado do zero (dados reais coletados
  de novo no banco `atlas_real`).

## 2026-10-21 — M1 concluída (issue #3, PR #28)

- API: `422 unknown_parameter` para parâmetros não declarados (inclusive campos de modelos de query) e
  `422 repeated_parameter` para escalares repetidos.
- Filtro temporal: a primeira versão (sobreposição de períodos) foi rejeitada pelo qa-auditor, porque
  incluía a posição de 31/03 num intervalo encerrado em 15/03. A regra final, validada pelo economist, é
  "o período de referência termina no intervalo", com novo índice `period_end` (migração 0004; o
  Seq Scan virou Index Scan). Datas efetivas da resposta simétricas.
- Frontend: presets alinhados ao 1º dia do mês, domínio do eixo a partir do mês inicial, "Atualizando…",
  nova tentativa em todos os erros, erro do catálogo visível.
- Processo: a validação por clone limpo pegou erros de ruff que quebrariam o CI. Criado
  `scripts/check.sh`, espelho dos gates do CI (recusa o banco de dados reais), e `alembic check` no CI.
- Testes: 113 pytest e 46 vitest; regressões comprovadas (falham sem a correção). Duas auditorias do
  qa-auditor; a final deu "pronto para PR".

## 2026-10-21 — Decisão de escopo: exclusão de funcionalidades com LLM (ADR 0004)

- Decisão permanente do mantenedor: o produto não terá funcionalidades baseadas em LLM.
- Atualizados: `PROJECT_SPEC.md` (§3, §19, §23, §24, com nota no topo), `CLAUDE.md` (regra 9), roadmap,
  AGENT_POLICY e STATE; ADR 0004 registrado.
- Backlog: issue #26 (A7) fechada como *not planned*; #27 (v1.0.0) passa a depender de A1–A6.
- Desenvolvimento autônomo retomado na M1 (#3).

## 2026-10-21 — Ativação da autonomia e M1 (issue #3)

- Orquestração criada: roadmap, AGENT_POLICY, DEFINITION_OF_DONE, STATE e este log; `CLAUDE.md`
  atualizado com a política de merge autônomo condicionado aos gates.
- Backlog no GitHub: issues #3–#27 (Fases 1–3, I1 de infraestrutura), com labels `phase:*`, `type:*`,
  `priority:*`, `autonomous:yes` e `agent:blocked`.
- Bloqueios registrados: proteção de branch e auto-merge nativo (#10) e GitHub Projects.

## 2026-10-21 — PR #2: DBGG/PIB (SGS 13762) e gráficos sincronizados

- Coleta real de 237 pontos conferida integralmente contra a API oficial; recoleta integral das séries
  mensais (revisões do PIB).
- Falhas corrigidas antes do merge: recursão infinita entre `echarts.connect` e a sincronização manual;
  cursor associando o mês seguinte (38 casos em 5 anos); zoom dessincronizado após redesenho.
- CI verde na 1ª execução; integrado pelo mantenedor.

## 2026-10-21 — PR #1: fundação e meta Selic (SGS 432)

- Conector BCB com janelas de 1 ano (as de 10 anos estouravam o timeout); ingestão idempotente e atômica.
- Falhas corrigidas: "hoje" calculado em UTC gravava D+1 (achado do qa-auditor); `rowcount = -1` no
  insert multi-linha; `public/` não versionado quebraria o Docker; typecheck dependia de `.next/` local.
- Identidade Git do mantenedor e desativação da coautoria configuradas; CI com 3 jobs.
