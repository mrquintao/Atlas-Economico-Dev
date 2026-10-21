# ADR 0001 — Stack e estrutura do monorepo

**Status:** aceito (2026-10-21)

**Decisão:** seguir a stack do PROJECT_SPEC §7 em um monorepo simples (`apps/web`, `services/api`,
`infra/docker`, `docs`, `scripts`). O diretório `packages/shared` sugerido na spec **não** foi criado:
ainda não há código compartilhado entre Python e TypeScript. Os tipos do frontend (`src/types/api.ts`)
espelham os esquemas Pydantic; gerar tipos a partir do OpenAPI fica para quando a API crescer.

**Detalhes:**
- Python gerenciado com **uv** (lockfile reprodutível, rápido); SQLAlchemy síncrono + psycopg 3 —
  a carga é baixa e o modelo síncrono é mais simples de testar.
- **Ingestão como CLI**, não como rota HTTP: evita expor operações de escrita e acoplar coleta a requisições.
- **Frontend busca dados no cliente** (página estática + fetch após hidratação): o build não depende da
  API estar no ar e o painel é inerentemente interativo (filtros). Next 16 com `cacheComponents` proíbe
  `new Date()` durante o prerender, por isso o período inicial é a constante "desde 2008".
- **shadcn/ui:** os componentes atuais (Card, grupo de botões) foram escritos no mesmo padrão
  (Tailwind + `cn()`), sem o CLI. O CLI do shadcn será adotado quando forem necessários primitivos
  complexos (Select, Dialog, Popover).
- **ECharts** importado de forma modular (`echarts/core`) para reduzir o bundle.
- **happy-dom** no Vitest em vez de jsdom: o jsdom 30 + vitest 5 dispara um bug do npm 10 na
  resolução de peer dependencies opcionais.
