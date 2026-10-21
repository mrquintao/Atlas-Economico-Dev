# Atlas Econômico Brasileiro

Plataforma apartidária de visualização da evolução histórica de indicadores econômicos e fiscais
do Brasil, construída **exclusivamente com dados oficiais** (Banco Central, IBGE, Tesouro Nacional,
SICONFI) e com rastreabilidade completa: cada número exibido informa fonte, série, unidade,
metodologia e data da última coleta.

> **Estado atual (iteração 2):** dados oficiais da **meta Selic (SGS 432)** e da **dívida bruta do
> governo geral / PIB (SGS 13762)**, com gráficos sincronizados no mesmo período, eixo de datas, zoom
> e cursor. IPCA 12 meses é a próxima etapa; a expansão estadual vem na fase 2.

![Dashboard](docs/screenshots/desktop.png)

## Objetivos

- Reunir séries econômicas oficiais em um banco próprio, com atualização automatizável e histórico de revisões.
- Exibir indicadores cronologicamente, com intervalo configurável, zoom, tooltips e comparação.
- Identificar claramente a fonte e a metodologia de cada informação; nunca inventar ou interpolar valores.
- Preparar a arquitetura para dados estaduais (geografia já modelada com códigos IBGE).

Especificação completa: [`PROJECT_SPEC.md`](PROJECT_SPEC.md). Instruções para agentes/colaboradores: [`CLAUDE.md`](CLAUDE.md).

## Stack

| Camada | Tecnologias |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Apache ECharts 6 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, httpx |
| Banco | PostgreSQL 16 |
| Testes | pytest (unitário + integração com PostgreSQL), Vitest + Testing Library |
| Infra | Docker, Docker Compose, GitHub Actions |

## Estrutura

```
apps/web/                 Frontend Next.js (src/app, src/features/dashboard, src/lib, src/hooks…)
services/api/             Backend FastAPI
  app/integrations/bcb/   Conector do SGS/BCData (janelas, retry, validação)
  app/ingestion/          Pipeline idempotente + CLI de coleta
  app/api/v1/             Endpoints REST
  migrations/             Alembic (schema + seed do catálogo)
  tests/                  pytest
infra/docker/             Dockerfiles
scripts/ingest.sh         Coleta incremental (para cron)
docs/                     Arquitetura, catálogo, metodologia, API, pipeline, decisões
```

## Pré-requisitos

- **Docker + Docker Compose** (caminho mais simples), **ou**
- Execução local: Python 3.12, [uv](https://docs.astral.sh/uv/) ≥ 0.11, Node.js 22, PostgreSQL 16.

## Opção A — Docker Compose

```bash
cp .env.example .env                       # ajuste credenciais se quiser
docker compose up --build -d               # db + api (aplica migrações ao iniciar) + web
docker compose exec api python -m app.ingestion.cli ingest SELIC_TARGET --full   # coleta inicial (~1–2 min)
docker compose exec api python -m app.ingestion.cli ingest DBGG_GDP               # série mensal (segundos)
```

- Frontend: http://localhost:3000
- API / OpenAPI: http://localhost:8000/docs

## Opção B — Execução local

### 1. Banco de dados

```bash
# com um PostgreSQL 16 local (ou: docker compose up -d db)
psql -U postgres -c "CREATE USER atlas WITH PASSWORD 'atlas' CREATEDB;"
psql -U postgres -c "CREATE DATABASE atlas OWNER atlas;"
psql -U postgres -c "CREATE DATABASE atlas_test OWNER atlas;"   # apenas para testes
```

### 2. Backend

```bash
cd services/api
cp ../../.env.example .env                 # DATABASE_URL etc.
uv sync                                    # cria .venv com Python 3.12 e dependências
uv run alembic upgrade head                # migrações + seed (BCB, Brasil, SELIC_TARGET, DBGG_GDP)
uv run python -m app.ingestion.cli ingest SELIC_TARGET --full   # coleta inicial do histórico completo
uv run python -m app.ingestion.cli ingest DBGG_GDP               # dívida bruta/PIB (série mensal)
uv run uvicorn app.main:app --reload --port 8000
```

Coletas seguintes são incrementais (re-buscam os últimos 90 dias para detectar revisões):

```bash
uv run python -m app.ingestion.cli ingest SELIC_TARGET
# ou, para agendar via cron:  scripts/ingest.sh
```

### 3. Frontend

```bash
cd apps/web
npm ci                                     # use npm ci (ver nota abaixo)
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev                                # http://localhost:3000
```

> **Nota:** instale com `npm ci` (usa o lockfile). Regenerar o lockfile do zero com npm 10 aciona um
> bug conhecido do npm com o vitest 5; use npm ≥ 11 (`npx npm@11 install`) nesse caso.

## Testes e qualidade

```bash
# Backend (os testes de integração recriam o schema do banco indicado!)
cd services/api
TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_test uv run pytest
uv run ruff check . && uv run ruff format --check .

# Frontend
cd apps/web
npm run lint && npm run typecheck && npm test && npm run build
```

Sem `TEST_DATABASE_URL`, os testes que dependem de PostgreSQL são ignorados (skip) e apenas os
unitários rodam. Nenhum teste acessa a internet. O CI (GitHub Actions) roda tudo isso a cada push/PR.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Catálogo de indicadores](docs/indicators.md)
- [Metodologias](docs/methodology.md)
- [Endpoints da API](docs/api.md)
- [Pipeline de ingestão](docs/data-pipeline.md)
- [Decisões técnicas (ADRs)](docs/adr/)

## Fontes de dados

| Fonte | Uso | Links |
|---|---|---|
| Banco Central do Brasil — SGS | Meta Selic (432) · DBGG/PIB (13762) | [Dados abertos](https://dadosabertos.bcb.gov.br/) · [SGS 432](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom) · [SGS 13762](https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008) |
| IBGE — SIDRA | Próximo: IPCA 12 meses (tabela 1737) | [API SIDRA](https://apisidra.ibge.gov.br/) · [Serviço de dados](https://servicodados.ibge.gov.br/api/docs/) |
| Tesouro Nacional / SICONFI | Fase 2 (estados) | [Tesouro Transparente](https://www.tesourotransparente.gov.br/) · [SICONFI API](https://apidatalake.tesouro.gov.br/docs/siconfi/) |

## Princípios

Dados reais apenas · transparência metodológica · integridade das definições ·
variações de taxas em pontos percentuais (p.p.) · neutralidade política (correlação ≠ causalidade).
