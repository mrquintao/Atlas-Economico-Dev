# Registro de execuções

Entradas curtas, da mais recente para a mais antiga: o que foi entregue, o que foi validado, as falhas e
como foram corrigidas, e as decisões relevantes. Os detalhes ficam nos PRs, nas issues e nos ADRs.

## 2026-10-21 — S4: indicadores fiscais estaduais (issue #14, PR #41)

- Economist: mapeamento de 9 indicadores (uma linha publicada cada; `cod_conta` e coluna exatos),
  ~130 requisições à API oficial, parecer em `docs/state-fiscal-indicators.md`. Ajustes ao escopo da
  issue: resultados primário/nominal só desde 2023 (sem RPPS, MDF 13ª ed.), DCL/RCL desde 2020
  (denominador ajustado), pessoal só do Executivo (R$ e %), e DC e investimentos acrescentados.
- Código: `fiscal_indicators.py` (derivação idempotente, revisões, lacunas, ambiguidade falha),
  `fiscal_catalog.py`, migração 0009 (frequências `bimonthly`/`four_monthly` + seed), CLI
  `derive-fiscal [--collect]`, ADR 0010; `ingest --all`/agendador ignoram a fonte SICONFI.
- Coleta real 2025, 27 UFs: 1.053 observações, 0 lacunas, 0 ambiguidades; idempotência; 54 amostras e
  5 conferências independentes na API sem divergência.
- qa-auditor: 0 crítico/alto; 4 médios corrigidos (estatísticas sobre fluxos acumulados no ano,
  "última coleta" de indicador derivado, testes de poder/esfera/coluna do período sobreviviam a
  mutação, verificação real pendente) e baixos corrigidos ou registrados no ADR 0010.
- Validação: `scripts/check.sh` verde (348 pytest, 73 vitest), E2E local 11/11.

## 2026-10-21 — S3 concluída: conector SICONFI (issue #13, PR #40)

- Reivindicação anterior da S3 (sessão `l0gdx7`, 05:50 UTC) sem branch nem PR em 3 h: assumida às 08:49 UTC.
- Conector `integrations/tesouro/siconfi.py` (RREO, RGF, extrato de entregas; ≤ 1 req/s, retry, paginação
  ORDS, `Decimal` exato); camada bruta `fiscal_reports`/`fiscal_report_rows` (migração 0008, ADR 0009);
  coleta incremental guiada pelo `extrato_entregas`; CLI `ingest-siconfi`.
- Coleta real: SP e RJ, 2024, RREO-Anexo 03 e RGF-Anexo 02 (18 anexos, 5.452 linhas, 22 requisições); 8
  anexos idênticos à API oficial; recoleta só pede o extrato.
- economist: códigos de esfera corrigidos (`C`, não `D`), RGF semestral recusado, DCL é do ente; DF conferido.
- qa-auditor: sem críticos; corrigidos H1 (retificação ainda não refletida no data lake → `awaiting_source`),
  M1 (anexo inválido), M2 (contagens após rollback) e baixos L1, L2, L3, L4, L6, L8.
- Ambiente: sessão sem `/tmp/pgdata`; PostgreSQL 16 recriado (`atlas` só com os anexos da S3).

## 2026-10-21 — S2: malhas oficiais das 27 UFs (issue #12, PR #39)

- A S3 (#13) estava reivindicada por outra sessão (sem branch publicado); para evitar trabalho
  duplicado, esta sessão executou a S2, também liberada pela S1.
- Conector da API de malhas v3 do IBGE (edição 2022, `qualidade=minima`), tabela versionada
  `geographic_boundaries` (migração 0007), CLI `ingest-boundaries` e endpoint GeoJSON
  `/api/v1/geographies/states/boundaries` com ETag fraco, `304` e gzip (~100 KB → ~28 KB).
- Validação real: 27 feições casando 1:1 com `geographic_units`; recoleta idempotente; geometrias
  servidas idênticas à fonte oficial (consulta nacional e por UF). Edições publicadas para esta
  consulta: 2019–2022 (as demais respondem HTTP 500).
- qa-auditor: 0 crítico/alto; 1 médio (`mesh_year` enorme gerava 500 no banco) e 7 baixos (ETag sem
  comparação fraca/`*`, ETag forte com gzip e sem `Vary` no 304, ETag mudando a cada recoleta,
  mensagem enganosa para edição inexistente, docstring, OpenAPI sem schema GeoJSON, `codarea` com
  dígitos Unicode, ilhas oceânicas omitidas não documentadas): todos corrigidos com testes ou
  documentados.
- Testes: 255 pytest; `scripts/check.sh` verde.

## 2026-10-21 — S1: 5 regiões e 27 UFs com códigos IBGE (issue #11, PR #38)

- Migração 0006 com as unidades conferidas contra `servicodados.ibge.gov.br/api/v1/localidades`
  (5 regiões, 27 UFs; conferência independente do qa-auditor sem divergências); hierarquia
  país → região → UF. `/geographies` ganhou o filtro `level` e o campo `parent`.
- Achado de projeto: códigos e siglas do IBGE só são únicos por nível (`1` = Brasil e Norte; `SE` =
  Sergipe e Sudeste). A unicidade passou a ser por nível, e a ingestão, que buscava o Brasil só pelo
  código `1`, passou a filtrar o nível (sem isso, gravaria séries nacionais na Região Norte conforme a
  ordem física da tabela). Teste de regressão comprovado: falha sem a correção.
- qa-auditor: 1 médio (o teste de regressão passava sem a correção) e 4 baixos, todos corrigidos.
- Testes: 210 pytest; `scripts/check.sh` verde.

## 2026-10-21 — Release v0.1.0 publicada (M7 concluída, issue #9)

- Workflow `Release` disparado na `main` com CI verde em `ade5512`: [execução
  39546442554](https://github.com/mrquintao/Atlas-Economico-Dev/actions/runs/39546442554) criou a
  tag e a [release `v0.1.0`](https://github.com/mrquintao/Atlas-Economico-Dev/releases/tag/v0.1.0)
  com as notas de `docs/releases/v0.1.0.md`.
- Uma segunda execução (39546540621, disparada 1 minuto depois) foi recusada pela verificação de tag
  existente, sem efeito sobre a release.
- Fase 1 concluída. Próxima: S1 (#11).

## 2026-10-21 — M7: critérios de aceite do MVP verificados; release v0.1.0 preparada (issue #9, PR #36)

- Verificação do §25 em clone limpo da `main` (`1dcd398`), seguindo só a Opção B do README, com um
  banco novo:
  - migrações 0001–0005;
  - coleta real de 10.093, 237 e 550 observações;
  - recoleta com 0 inserções e 0 revisões, e datas distintas iguais ao total;
  - OpenAPI;
  - filtro por data com agregação declarada;
  - site com dados reais.
  Evidências item a item em `docs/releases/v0.1.0.md`.
- 15 amostras conferidas contra as APIs oficiais (SGS 432 e 13762, SIDRA 1737/2265), todas iguais. A
  série DBGG inteira (237 meses) também confere, com 0 divergências.
- O README tinha um `/docs` perdido no fim do aviso de segurança, que pertencia ao link da OpenAPI.
  Corrigido, e a lista de endereços foi movida para a Opção A. Capturas de tela atualizadas a partir
  do build de produção.
- Contraste da navegação medido: 7,58:1 no tema claro e 7,34:1 no escuro (achado da M5 resolvido).
- Novo workflow `Release` (`workflow_dispatch` na `main`): só cria a tag e a release se versão, notas,
  ausência de tag e os 4 checks obrigatórios do commit estiverem em ordem. As ferramentas do agente
  não criam releases diretamente. A tag é criada depois do merge, pelo workflow; o resultado fica
  registrado numa entrada própria.

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
