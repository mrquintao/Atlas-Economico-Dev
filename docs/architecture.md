# Arquitetura

```
 Fontes oficiais (BCB SGS, IBGE SIDRA e Malhas, SICONFI; futuramente Tesouro)
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
- **Geografia de primeira classe**: `geographic_units` com código IBGE: Brasil (`1`), 5 regiões e
  27 UFs (migração 0006, conferida contra a API de localidades do IBGE). Código e sigla são únicos
  por nível (`1` também é a Região Norte; `SE`, Sergipe e Sudeste).
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
| `geographic_units` | País/região/UF/município com código IBGE e hierarquia (`parent_id`: país → região → UF) |
| `geographic_boundaries` | Geometria oficial (GeoJSON em `JSONB`) de cada unidade por edição da malha do IBGE (`mesh_year`) e qualidade, com hash, URL da consulta e data da coleta |
| `fiscal_reports` | Camada bruta do SICONFI (S3): um anexo do RREO/RGF por UF, exercício, período, esfera e poder, com hash do conteúdo, data da entrega (`extrato_entregas`), URL da consulta e data da coleta |
| `fiscal_report_rows` | Cada valor publicado no anexo (`rotulo`, `coluna`, `cod_conta`, `conta`, `NUMERIC(24,8)`); base dos indicadores fiscais estaduais (S4) |
| `observations` | Valores (`NUMERIC(24,8)`), período de referência, `collected_at`, referência da fonte. Nos indicadores estaduais do SICONFI (S4, ADR 0010), derivados de uma linha de `fiscal_report_rows`, `metadata_json` aponta o anexo e a linha de origem |
| `ingestion_runs` | Auditoria de cada coleta: status, contagens, erro, janelas consultadas e SHA-256 de cada payload |
| `observation_revisions` | Valor anterior/novo quando a fonte revisa um dado já publicado |

Índices: unicidade (indicador, geografia, data de referência); `(indicador, geografia, period_end)`,
que atende ao filtro de intervalo das consultas (ADR 0005); e índice por `reference_date`.

## Frontend

- `src/app/` — layout com navegação (`Brasil`, `Estados`, `Metodologia`, `Fontes de dados`) e páginas
  (estáticas; dados buscados no cliente após hidratação): `/`, `/estados`, `/estados/[uf]`,
  `/metodologia` e `/fontes`. As 27 páginas `/estados/[uf]` são pré-renderizadas a partir da lista de
  UFs em `src/lib/states.ts` (a mesma da migração 0006, conferida por teste).
- `src/proxy.ts` — Proxy do Next.js 16 restrito a `/estados/:uf`: sigla em minúsculas → `308` para a
  página canônica (`/estados/mg` → `/estados/MG`); qualquer outro segmento (`XX`, `BR`, código IBGE)
  → página `not-found` com status `404`. A verificação precisa ocorrer antes da renderização: a página
  é transmitida em streaming e um `notFound()` dentro dela só produziria a página de erro com status 200.
- `src/features/dashboard/` — painel nacional, filtro de período, cartões, gráfico, metodologia.
  O gráfico e a sincronização servem a qualquer frequência: diária, mensal, bimestral (RREO) e
  quadrimestral (RGF). Um ponto de período vale pelo seu último dia ao alinhar o cursor (um
  quadrimestre destaca o seu último bimestre); lacunas de período quebram a linha; nos fluxos
  acumulados no ano a linha também é interrompida na virada do ano (o valor de janeiro recomeça a
  acumulação).
- `src/features/states/` — página da UF sobre `GET /states/{uf}/dashboard` (cartões com o último
  valor, período de referência, janela de acumulação e diferença para o mesmo período do ano
  anterior) e `GET /states/{uf}/indicators` (uma requisição para todas as séries do intervalo).
  Indicadores sem dados da UF não têm cartão nem gráfico e são listados como ausentes; UF sem nenhum
  dado mostra só o aviso. A ressalva do DF (`notes`) aparece em destaque.
- `src/features/catalog/` — páginas de catálogo: `/metodologia` lista todos os indicadores de
  `GET /api/v1/indicators` e `/fontes` as fontes de `GET /api/v1/sources` com os indicadores de cada
  uma. `IndicatorMetadata` também é usado no painel de metodologia de cada gráfico: nenhum texto
  metodológico fica no frontend, tudo vem do catálogo (seeds das migrações). Âncoras por código
  (`/metodologia#SELIC_TARGET`, `/fontes#BCB`).
  O intervalo de datas é estado único do painel e é repassado a todos os gráficos (sincronização).
- `src/lib/format.ts` — formatação pt-BR reutilizável (vírgula decimal, `p.p.`, datas sem fuso,
  valores em reais com escala explícita — `R$ 268,00 bi` —, bimestres `6º bim./2025 (nov–dez)` e
  quadrimestres `3º quadr./2025 (set–dez)`).
- `src/lib/period.ts` — períodos predefinidos (5 anos, 10 anos, desde 2008, todo o histórico).
- `src/hooks/useObservations.ts` — carregamento com estados de loading/erro/sucesso e cancelamento.
