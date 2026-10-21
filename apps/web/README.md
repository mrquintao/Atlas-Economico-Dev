# @atlas/web — frontend do Atlas Econômico Brasileiro

Next.js 16 + TypeScript + Tailwind 4 + Apache ECharts. Consome **apenas** a API interna
(`NEXT_PUBLIC_API_BASE_URL`, padrão `http://localhost:8000`).

```bash
npm ci
npm run dev          # http://localhost:3000
npm test             # Vitest + Testing Library (happy-dom)
npm run lint && npm run typecheck && npm run build
```

- `src/features/dashboard/` — painel "Brasil em Perspectiva" (filtros, cartões, gráfico, metodologia)
- `src/lib/format.ts` — formatação pt-BR (use sempre estas funções)
- `src/lib/period.ts` — períodos predefinidos compartilhados por todos os gráficos

Instruções completas no [README da raiz](../../README.md).
