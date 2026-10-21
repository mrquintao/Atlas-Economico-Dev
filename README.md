# Atlas Econômico Brasileiro

Plataforma apartidária de visualização da evolução histórica de indicadores econômicos e fiscais
do Brasil, construída **exclusivamente com dados oficiais** (Banco Central, IBGE, Tesouro Nacional,
SICONFI) e com rastreabilidade completa: cada número exibido informa fonte, série, unidade,
metodologia e data da última coleta.

> **Estado atual (iteração 3):** dados oficiais da **meta Selic (BCB SGS 432)**, da **dívida bruta do
> governo geral / PIB (BCB SGS 13762)** e do **IPCA acumulado em 12 meses (IBGE SIDRA 1737, variável
> 2265)**, com três gráficos sincronizados no mesmo período, eixo de datas, zoom e cursor. A expansão
> estadual vem na fase 2.

![Dashboard](docs/screenshots/desktop.png)

<sub>Cursor sincronizado por data entre os gráficos: [captura](docs/screenshots/desktop-sync.png).</sub>

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
apps/web/                 Frontend Next.js (src/app, src/features/{dashboard,catalog}, src/lib, src/hooks…)
services/api/             Backend FastAPI
  app/integrations/       Conectores BCB/SGS e IBGE/SIDRA (janelas, retry, validação)
  app/ingestion/          Pipeline idempotente + CLI de coleta
  app/api/v1/             Endpoints REST
  migrations/             Alembic (schema + seed do catálogo)
  tests/                  pytest
infra/docker/             Dockerfiles
scripts/dev.sh            Executa o projeto localmente com um único comando (ver "Início rápido")
scripts/ingest.sh         Coleta incremental de todos os indicadores (para cron)
docs/                     Arquitetura, catálogo, metodologia, API, pipeline, decisões
```

## Pré-requisitos

- **Docker + Docker Compose** (caminho mais simples), **ou**
- Execução local: Python 3.12, [uv](https://docs.astral.sh/uv/) ≥ 0.11, Node.js 22, PostgreSQL 16.

## Início rápido

Um único comando prepara e executa o projeto (Linux, macOS ou WSL):

```bash
scripts/dev.sh                    # local: verifica pré-requisitos e o PostgreSQL, cria os .env,
                                  # instala dependências, aplica migrações, faz a primeira coleta
                                  # (banco vazio) e sobe API (:8000) e painel (:3000). Ctrl+C encerra.
scripts/dev.sh --db-docker        # idem, subindo só o PostgreSQL com Docker Compose
scripts/dev.sh data               # coleta incremental dos indicadores nacionais e da malha das UFs
scripts/dev.sh data --states 2025 # + indicadores fiscais estaduais de 2025 (SICONFI, ~10 min)
scripts/dev.sh docker             # tudo com Docker Compose (db, api, web) + primeira coleta
scripts/dev.sh --help
```

- O modo local espera um PostgreSQL 16 com o banco configurado em `services/api/.env` (padrão:
  `atlas`/`atlas` em `localhost:5432/atlas`; veja "Opção B, 1. Banco de dados"), ou use `--db-docker`.
- A primeira coleta (só num banco vazio) busca os dados oficiais: a série diária da Selic desde 1999
  leva de 2 a 4 minutos. Se a rede falhar, o script avisa e sobe a aplicação mesmo assim; os logs
  ficam em `.dev/logs/`. O script nunca apaga dados.
- Portas: `API_PORT=8010 WEB_PORT=3010 scripts/dev.sh` (o painel passa a usar a API dessa porta).

As seções abaixo descrevem os mesmos passos manualmente.

## Opção A — Docker Compose

```bash
cp .env.example .env                       # configure as credenciais de desenvolvimento
docker compose up --build -d               # db + api (aplica migrações ao iniciar) + web
docker compose exec api python -m app.ingestion.cli ingest SELIC_TARGET --full   # coleta inicial (~1–2 min)
docker compose exec api python -m app.ingestion.cli ingest DBGG_GDP               # série mensal (segundos)
docker compose exec api python -m app.ingestion.cli ingest IPCA_12M               # IBGE/SIDRA (segundos)
docker compose exec api python -m app.ingestion.cli ingest --all                  # todos, incremental
docker compose exec api python -m app.ingestion.cli ingest-boundaries             # malha das 27 UFs (IBGE)
docker compose exec api python -m app.ingestion.cli ingest-siconfi --report RGF --annex "RGF-Anexo 02" --state SP --year 2024  # SICONFI
```

- Frontend: http://localhost:3000 (painel nacional; estados em `/estados`, `/estados/SP` e `/estados/comparar`; catálogo em `/metodologia` e `/fontes`)
- API: http://localhost:8000 · documentação OpenAPI interativa em http://localhost:8000/docs
- PostgreSQL: `127.0.0.1:5432` (acessível apenas a partir do computador local; a API usa a rede interna do Compose).

### Coleta automática

O serviço opcional `scheduler` mantém os dados atualizados, sem filas nem serviços pagos:

```bash
# INGEST_SCHEDULE: horários do dia (HH:MM, separados por vírgula), no fuso de Brasília. Padrão: 06:00.
INGEST_SCHEDULE=06:00,18:30 docker compose --profile scheduler up --build -d
docker compose logs -f scheduler                       # próxima execução e resultado de cada coleta
docker compose exec scheduler python -m app.ingestion.scheduler --check   # valida a configuração
```

- A falha de um indicador não impede os demais e fica registrada em `ingestion_runs`.
- `INGEST_ON_START=true` também coleta ao iniciar o serviço (útil num banco recém-criado).
- O painel "Sobre o indicador e a metodologia" mostra a última coleta bem-sucedida e avisa quando a
  última tentativa falhou. Detalhes em [docs/data-pipeline.md](docs/data-pipeline.md#coleta-automática).

> **Segurança:** os valores `atlas/atlas` são exemplos para desenvolvimento. Nunca reutilize essas credenciais nem este Compose sem adaptação em um servidor público.

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
uv run alembic upgrade head                # migrações + seed (BCB, IBGE, Brasil, SELIC_TARGET, DBGG_GDP, IPCA_12M)
uv run python -m app.ingestion.cli ingest SELIC_TARGET --full   # coleta inicial do histórico completo
uv run python -m app.ingestion.cli ingest DBGG_GDP               # dívida bruta/PIB (série mensal)
uv run python -m app.ingestion.cli ingest IPCA_12M               # IPCA 12 meses (IBGE/SIDRA)
uv run python -m app.ingestion.cli ingest-boundaries             # malha oficial das 27 UFs (IBGE, edição 2022)
uv run python -m app.ingestion.cli ingest-siconfi --report RREO --annex "RREO-Anexo 03" --state SP --year 2024  # anexo do SICONFI
uv run uvicorn app.main:app --reload --port 8000   # API em :8000, OpenAPI em http://localhost:8000/docs
```

Coletas seguintes são incrementais: séries diárias re-buscam os últimos 90 dias e séries mensais
são recoletadas inteiras (revisões do PIB podem alterar anos anteriores):

```bash
uv run python -m app.ingestion.cli ingest SELIC_TARGET
uv run python -m app.ingestion.cli ingest DBGG_GDP
uv run python -m app.ingestion.cli ingest IPCA_12M
uv run python -m app.ingestion.cli ingest --all   # todos (código de saída 1 se algum falhar)
# ou, para agendar via cron do sistema:  scripts/ingest.sh
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

# E2E (Playwright) sobre banco descartável com fixture sintética: ver docs/testing-e2e.md
npm run test:e2e
```

Sem `TEST_DATABASE_URL`, os testes que dependem de PostgreSQL são ignorados (skip) e apenas os
unitários rodam. Nenhum teste acessa a internet. O CI (GitHub Actions) roda tudo isso a cada push/PR.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Catálogo de indicadores](docs/indicators.md)
- [Metodologias](docs/methodology.md)
- [Endpoints da API](docs/api.md)
- [Pipeline de ingestão](docs/data-pipeline.md)
- [Testes E2E](docs/testing-e2e.md)
- [Releases e verificação dos critérios de aceite](docs/releases/)
- [Decisões técnicas (ADRs)](docs/adr/)

## Fontes de dados

| Fonte | Uso | Links |
|---|---|---|
| Banco Central do Brasil — SGS | Meta Selic (432) · DBGG/PIB (13762) | [Dados abertos](https://dadosabertos.bcb.gov.br/) · [SGS 432](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom) · [SGS 13762](https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008) |
| IBGE — SIDRA | Implementado: IPCA 12 meses (tabela 1737, variável 2265) | [API SIDRA](https://apisidra.ibge.gov.br/) · [Serviço de dados](https://servicodados.ibge.gov.br/api/docs/) |
| IBGE — Malhas | Implementado: geometrias oficiais das 27 UFs (edição 2022) | [API de malhas v3](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) |
| Tesouro Nacional / SICONFI | Fase 2 (estados) | [Tesouro Transparente](https://www.tesourotransparente.gov.br/) · [SICONFI API](https://apidatalake.tesouro.gov.br/docs/siconfi/) |

## Princípios

Dados reais apenas · transparência metodológica · integridade das definições ·
variações de taxas em pontos percentuais (p.p.) · neutralidade política (correlação ≠ causalidade).

## Licença

Distribuído sob a [licença MIT](LICENSE). Consulte também a [auditoria de segurança pré-publicação](docs/security/publication-audit.md).
