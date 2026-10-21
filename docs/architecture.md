# Arquitetura

```
 Fontes oficiais (BCB SGS; futuramente IBGE SIDRA, Tesouro, SICONFI)
        │  HTTPS (httpx: timeout, retry com backoff, rate limit, validação)
        ▼
 services/api/app/integrations/      conectores — 1 por fonte
        ▼
 services/api/app/ingestion/         validação, normalização, upsert idempotente,
        │                            detecção de revisões, registro em ingestion_runs
        ▼
 PostgreSQL                          catálogo genérico + observations (NUMERIC)
        ▼
 services/api/app/api/v1/            FastAPI (REST, OpenAPI, erros JSON consistentes)
        ▼
 apps/web/                           Next.js — consome só a API interna
        ▼
 Dashboard (ECharts)
```

## Princípios de desenho

- **Monorepo simples**, sem microserviços: um backend (API + ingestão como CLI) e um frontend.
- **Frontend nunca chama fontes externas.** Isso permite cache, validação, controle de limites e histórico.
- **Modelo genérico de indicadores**: novos indicadores são linhas em `indicators`; os valores
  vão todos para `observations` (chave única `indicator_id + geographic_unit_id + reference_date`).
- **Geografia de primeira classe**: `geographic_units` com código IBGE (Brasil = `1`), pronta para UFs.
  A API recusa servir uma série nacional como se fosse estadual (`geography_not_available`).
- **Camadas** no backend, sem abstração excessiva:
  `integrations` (HTTP + parsing) → `ingestion` (regras de persistência) → `repositories` (SQL)
  → `services` (agregações/estatísticas) → `api` (HTTP).
- **Ingestão fora do ciclo de requisição**: CLI (`python -m app.ingestion.cli`) agendável por cron.

## Modelo de dados

| Tabela | Papel |
|---|---|
| `data_sources` | Fontes oficiais (BCB…) |
| `indicators` | Catálogo: código interno, série na fonte, unidade, unidade de variação (`p.p.`), frequência, nível geográfico, metodologia, link oficial |
| `geographic_units` | País/UF/município com código IBGE e hierarquia (`parent_id`) |
| `observations` | Valores (`NUMERIC(24,8)`), período de referência, `collected_at`, referência da fonte |
| `ingestion_runs` | Auditoria de cada coleta: status, contagens, erro, janelas consultadas e SHA-256 de cada payload |
| `observation_revisions` | Valor anterior/novo quando a fonte revisa um dado já publicado |

Índices: unicidade (indicador, geografia, data) — que também atende às consultas por intervalo —
e índice por `reference_date`.

## Frontend

- `src/app/` — layout e página (estática; dados buscados no cliente após hidratação).
- `src/features/dashboard/` — painel, filtro de período, cartões, gráfico, metodologia.
  O intervalo de datas é estado único do painel e é repassado a todos os gráficos (sincronização).
- `src/lib/format.ts` — formatação pt-BR reutilizável (vírgula decimal, `p.p.`, datas sem fuso).
- `src/lib/period.ts` — períodos predefinidos (5 anos, 10 anos, desde 2008, todo o histórico).
- `src/hooks/useObservations.ts` — carregamento com estados de loading/erro/sucesso e cancelamento.
