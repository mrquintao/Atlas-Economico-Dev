# CLAUDE.md — Atlas Econômico Brasileiro

Instruções gerais para qualquer agente (humano ou IA) que trabalhe neste repositório.
A especificação completa está em [`PROJECT_SPEC.md`](PROJECT_SPEC.md) e prevalece sobre este arquivo.

## Missão

Plataforma apartidária de visualização da evolução histórica de indicadores econômicos e
fiscais do Brasil, alimentada **exclusivamente por dados oficiais** (BCB, IBGE, Tesouro, SICONFI),
com rastreabilidade completa de cada número exibido.

## Regras inegociáveis

1. **Nenhum dado inventado.** Valores econômicos vêm de fontes oficiais. Dados sintéticos só
   em testes (`services/api/tests/fixtures/`) e devem ser identificados como tais.
2. **Nunca substituir ausência por zero** nem interpolar silenciosamente. Lacunas são exibidas como lacunas.
3. **Toda série carrega metadados**: fonte, código da série, unidade, frequência, metodologia,
   link oficial, data da última coleta.
4. **Integridade de definição**: não misturar conceitos (ex.: DBGG metodologia 2008 ≠ pré-2008;
   IPCA mensal ≠ 12 meses). Agregações (ex.: diário → mensal) devem ser explícitas e declaradas
   na resposta da API (`aggregation`).
5. **Variações de taxas em pontos percentuais (p.p.)**, nunca em "%". 10% → 12% = +2 p.p.
6. **Neutralidade**: não atribuir causalidade a governos/eventos. Correlação ≠ causalidade.
7. **Não declarar integração concluída sem verificação real** contra a fonte oficial.
8. **Escopo incremental**: não implementar fase 2 (estados/mapa) ou fase 3 (análises avançadas, grafos)
   antes da hora.
9. **Sem LLMs no produto (decisão permanente, [ADR 0004](docs/adr/0004-exclusao-de-funcionalidades-com-llm.md))**:
   nenhum assistente ou consulta em linguagem natural, chatbot, integração com APIs de LLM, RAG,
   embeddings/bancos vetoriais ou análise e relatório gerados por modelo. Toda análise é determinística e
   verificável. (Ferramentas de IA para *desenvolver* o projeto continuam permitidas.)

## Arquitetura (resumo)

```
Fontes oficiais → integrations/ (conectores httpx) → ingestion/ (validação, idempotência,
revisões) → PostgreSQL → FastAPI (/api/v1) → Next.js (apps/web) → ECharts
```

O frontend **nunca** chama APIs externas; só a API interna. Detalhes em `docs/architecture.md`.

## Estrutura

```
apps/web/            Next.js 16 + TypeScript + Tailwind 4 + ECharts
services/api/        FastAPI + SQLAlchemy 2 + Alembic + httpx (Python 3.12, gerenciado com uv)
  app/api/v1/        Rotas REST
  app/core/          Configuração, logging
  app/db/            Engine/sessão
  app/models/        Modelos ORM
  app/schemas/       Esquemas Pydantic de resposta
  app/integrations/  Conectores de fontes externas (ex.: bcb/sgs.py)
  app/ingestion/     Pipeline de ingestão (idempotente, registra execuções e revisões)
  app/repositories/  Consultas ao banco
  app/services/      Regras de negócio (agregações, resumos)
  migrations/        Alembic (inclui seed do catálogo)
  tests/             pytest (unitários + integração com PostgreSQL)
docs/                Arquitetura, catálogo, metodologia, endpoints, decisões (ADRs)
.claude/agents/      Agentes especializados
```

## Comandos

```bash
# Backend (de services/api)
uv sync                                   # instala dependências
uv run alembic upgrade head               # migrações + seed do catálogo
uv run python -m app.ingestion.cli ingest SELIC_TARGET   # coleta real do BCB
uv run uvicorn app.main:app --reload      # API em http://localhost:8000/docs
uv run pytest                             # testes (requer TEST_DATABASE_URL para integração)
uv run ruff check . && uv run ruff format --check .

# Frontend (de apps/web)
npm install
npm run dev                               # http://localhost:3000
npm test                                  # Vitest
npm run lint && npm run typecheck && npm run build

# Tudo via Docker
docker compose up --build
```

## Convenções

- **Idioma**: código, identificadores e commits em inglês; textos de interface e documentação
  voltada ao usuário em português do Brasil.
- **Python**: tipagem explícita, `ruff` (lint + format), SQLAlchemy 2 estilo `Mapped[...]`,
  valores econômicos como `Decimal`/`NUMERIC` (nunca `float` no banco).
- **TypeScript**: `strict`, sem `any`. Formatação numérica/datas sempre via `src/lib/format.ts` (pt-BR).
- **Datas**: ISO 8601 (`YYYY-MM-DD`) na API. O SGS usa `dd/mm/aaaa`; a conversão fica no conector.
- **Novos indicadores**: adicionar via migração de seed em `indicators` — nunca criar tabela por indicador.
- **Testes**: toda regra crítica (parsing, conversões, idempotência, filtros, agregações) tem teste.
  Testes nunca acessam a rede: usar `httpx.MockTransport` e fixtures locais.
- **Segredos**: só via variáveis de ambiente (`.env`, nunca commitado). Ver `.env.example`.
- **Commits**: pequenos, descritivos, no imperativo (`feat(api): ...`, `fix(web): ...`).
  **Não** adicionar trailers de coautoria ou sessão do Claude (`Co-Authored-By`, `Claude-Session`)
  — desativados em `.claude/settings.json` (`attribution.commit = ""`, `sessionUrl = false`).
  Commits saem com a identidade do mantenedor (`Mateus Quintão`, e-mail noreply do GitHub, sem
  assinatura), aplicada a cada sessão por `scripts/configure-git-identity.sh` (hook `SessionStart`).
  Nunca reescrever histórico publicado, usar force push ou fazer push direto na `main`.

## Desenvolvimento autônomo

O mantenedor autorizou o desenvolvimento autônomo, **inclusive o merge de PRs**, condicionado aos gates
de qualidade. Antes de qualquer trabalho, leia:

- [`docs/autonomy/STATE.md`](docs/autonomy/STATE.md): checkpoint (fase, próxima issue, bloqueios);
- [`docs/autonomy/AGENT_POLICY.md`](docs/autonomy/AGENT_POLICY.md): ciclo por entrega, **gate de merge**
  e proibições permanentes;
- [`docs/autonomy/DEFINITION_OF_DONE.md`](docs/autonomy/DEFINITION_OF_DONE.md): critérios de conclusão;
- [`docs/implementation-roadmap.md`](docs/implementation-roadmap.md): entregas por fase e dependências.

As tarefas vivem em GitHub Issues (labels `phase:*`, `type:*`, `priority:*`, `autonomous:yes`,
`agent:blocked`). Registre cada execução em [`docs/autonomy/RUN_LOG.md`](docs/autonomy/RUN_LOG.md).
Proibições inegociáveis: force push, reescrita de histórico, push direto na `main`, segredos no Git,
bypass ou desativação de checks e testes, operações destrutivas em dados reais, serviços pagos sem
orçamento, implantação pública de funcionalidade incompleta e qualquer funcionalidade do produto
baseada em LLM.

## Fluxo com agentes

O agente principal atua como **Tech Lead**: decompõe tarefas, delega e integra.

| Agente | Quando acionar |
|---|---|
| `economist` | Escolha/validação de séries, unidades, metodologia, textos explicativos, regras de agregação |
| `data-engineer` | Conectores, ingestão, modelagem, migrações, desempenho de consultas |
| `fullstack-developer` | Endpoints FastAPI, páginas Next.js, gráficos ECharts, acessibilidade |
| `qa-auditor` | Antes de cada entrega: testes, revisão adversarial, conferência de amostras com a fonte oficial |

Definição de pronto: [`docs/autonomy/DEFINITION_OF_DONE.md`](docs/autonomy/DEFINITION_OF_DONE.md).
