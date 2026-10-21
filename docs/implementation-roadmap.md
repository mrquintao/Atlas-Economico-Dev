# Roadmap de implementação

Decomposição do [`PROJECT_SPEC.md`](../PROJECT_SPEC.md) em entregas pequenas, verticais e ordenadas por
dependência. Cada entrega pendente tem uma issue no GitHub (fonte principal das tarefas); a coluna
**Issue** é atualizada quando a issue é criada. Estado corrente: [`autonomy/STATE.md`](autonomy/STATE.md).

Legenda de status: ✅ concluída · 🔄 em andamento · ⏳ pendente · ⛔ bloqueada.

## Fase 1 — MVP nacional (`phase:mvp`)

| ID | Entrega | Depende de | Spec | Status | Issue / PR |
|---|---|---|---|---|---|
| M0a | Fundação: monorepo, Docker Compose, PostgreSQL, FastAPI, modelagem, migrações, CI | — | §7–10, §27 | ✅ | PR #1 |
| M0b | Selic meta (SGS 432): conector BCB, ingestão idempotente, API, gráfico | M0a | §6.1, §11, §12, §27 | ✅ | PR #1 |
| M0c | Dívida bruta/PIB (SGS 13762) e gráficos sincronizados | M0b | §5, §6.1, §14 | ✅ | PR #2 |
| M1 | Robustez: parâmetros desconhecidos na API, filtros temporais de séries mensais, estados de carregamento | M0c | §12, §13G, §5 | ✅ | #3 · PR #28 |
| M2 | IPCA acumulado em 12 meses (IBGE/SIDRA 1737): conector IBGE, validação metodológica, cartão e gráfico | M1 | §6.2, §5 | ✅ | PR #30 |
| M3 | `GET /api/v1/dashboard/national` (resumo dos três indicadores) | M2 | §12 | ✅ | #5 · PR #32 |
| M4 | Automação da coleta: agendamento simples (serviço de agendamento no Compose) e monitoramento das execuções | M2 | §3.3, §7 Automação, §11 | ✅ | #6 · PR #33 |
| M5 | Páginas "Metodologia" e "Fontes de dados" geradas a partir do catálogo | M2 | §13, §22 | ✅ | #7 · PR #34 |
| M6 | Testes E2E (Playwright) do fluxo principal no CI | M2 | §7 Testes, §21.12 | ✅ | #8 · PR #35 |
| M7 | Verificação dos critérios de aceite do MVP e release `v0.1.0` | M2–M6 | §25 | ✅ | #9 · PR #36 · [`v0.1.0`](https://github.com/mrquintao/Atlas-Economico-Dev/releases/tag/v0.1.0) |
| I1 | Proteção da `main` com checks obrigatórios e auto-merge nativo | — | — | ⛔ | #10 |

## Fase 2 — Atlas estadual (`phase:states`)

| ID | Entrega | Depende de | Spec | Status | Issue |
|---|---|---|---|---|---|
| S1 | Unidades geográficas: 27 UFs e 5 regiões com códigos IBGE validados | M7 | §6.5, §10 | ✅ | #11 · PR #38 |
| S2 | Malhas IBGE: conector de geometrias (GeoJSON) e endpoint de geometrias | S1 | §6.5, §15 | ✅ | #12 · PR #39 |
| S3 | Conector SICONFI (RREO/RGF): limite de 1 req/s, paginação, retry, coleta incremental | S1 | §6.4, §11 | ✅ | #13 · PR #40 |
| S4 | Catálogo e normalização de indicadores fiscais estaduais (RCL, DC, DCL, DCL/RCL, pessoal, primário, nominal, investimentos), validados pelo economist | S3 | §16 | ✅ | #14 · PR #41 |
| S5 | API estadual: `/states/{uf}/indicators` e `/states/{uf}/dashboard` | S4 | §12 | ✅ | #15 · PR #42 |
| S6 | Mapa interativo do Brasil (D3 Geo): coroplético acessível, ausências explícitas, filtro temporal | S2, S5 | §15 | ✅ | #16 · PR #45 |
| S7 | Página por estado `/estados/[uf]` | S5 | §15, §16 | ✅ | #17 · PRs #43, #44 |
| S8 | Comparação entre estados e rankings com métricas relativas | S5, S7 | §16 | ✅ | #18 · PR #46 |
| S9 | Release `v0.2.0` (Atlas estadual) | S1–S8 | §23 | ⏳ | #19 |

## Fase 3 — Análise avançada (`phase:advanced`)

| ID | Entrega | Depende de | Spec | Status | Issue |
|---|---|---|---|---|---|
| A1 | Linha do tempo de eventos com fonte verificável e sobreposição nos gráficos | S9 | §18 | ⏳ | #20 |
| A2 | Valores corrigidos pela inflação (deflator IPCA, data-base selecionável) | M2, S4 | §23 F3 | ⏳ | #21 |
| A3 | Correlações estatísticas com defasagens (funções determinísticas) | M7 | §2C, §17 | ⏳ | #22 |
| A4 | Explorador de relacionamentos (grafo com tipos de vínculo) | A3 | §17 | ⏳ | #23 |
| A5 | Comparações entre governos/períodos, com neutralidade e sem atribuição causal | A1 | §4.4, §23 F3 | ⏳ | #24 |
| A6 | Relatórios exportáveis (CSV e PDF) | M7 | §23 F3 | ⏳ | #25 |
| A8 | Release `v1.0.0` | A1–A6 | §23, §29 | ⏳ | #27 |

Todas as análises da Fase 3 usam algoritmos convencionais e cálculos verificáveis.

## Fora do escopo

- **Permanente — funcionalidades baseadas em LLM** ([ADR 0004](adr/0004-exclusao-de-funcionalidades-com-llm.md)):
  assistente ou consultas em linguagem natural, chatbots, integrações com APIs de LLM, RAG, embeddings e
  bancos vetoriais, e análises ou relatórios gerados por modelo. A antiga entrega A7 (issue #26) foi
  cancelada sem substituição.
- **§24:** Neo4j, microserviços, Kubernetes, filas distribuídas, contas de usuário, modelos preditivos,
  análises eleitorais e coleta de todos os municípios. Não serão implementados sem registro e
  justificativa em ADR.
