# ADR 0008 — Testes E2E com Playwright sobre fixture sintética, fora do Docker Compose

**Status:** aceito (2026-10-21), issue #8 (M6).

## Contexto

A issue #8 pede testes de navegador do fluxo principal no CI (presets, cursor e zoom sincronizados,
troca diária/mensal, estado vazio, console sem erros), sem acessar as fontes oficiais, com API e banco
"do Docker Compose" populados por fixture sintética.

## Decisões

1. **`@playwright/test` em `apps/web/e2e`**, um único projeto Chromium (1280×900, `pt-BR`,
   `America/Sao_Paulo`), um worker e **sem retries**: uma falha intermitente é defeito a corrigir
   (AGENT_POLICY §4).
2. **Fixture sintética determinística** (`services/api/tests/fixtures/e2e_seed.py`), identificada em
   cada linha e protegida por três travas: `ATLAS_E2E_SEED=1`, nome do banco contendo `e2e` ou `test`
   (o padrão `atlas`, com dados reais, é recusado) e recusa de banco com observações ou execuções de coleta. Datas fixas tornam
   os presets ("5 anos" ancorado na última observação) e as asserções reprodutíveis.
3. **Sem Docker Compose no job E2E**: PostgreSQL como serviço do GitHub Actions; API (`uvicorn`) e site
   (`next start` do build de produção) iniciados pelo `webServer` do Playwright. Motivos: o job Docker já
   valida as imagens e o Compose; o E2E fica mais rápido, roda igual localmente (inclusive no ambiente
   em nuvem do agente, onde o proxy bloqueia o `ghcr.io`) e falhas apontam para a aplicação, não para a
   infraestrutura. O build de produção é o mesmo das imagens, mas o site roda com `next start`, e não
   com o `server.js` do modo `standalone` usado na imagem (o Next avisa disso no log). A topologia do
   Compose (URL da API embutida no build, rede entre contêineres, servidor `standalone`) continua
   coberta apenas pelo smoke test do job Docker.
4. **Teste caixa-preta**: leitura dos tooltips HTML do ECharts e dos nomes acessíveis dos gráficos, sem
   ganchos de teste no produto. Como todos os gráficos têm o mesmo `grid` fixo e o mesmo domínio, a
   mesma posição horizontal corresponde à mesma data.

## Consequências

- O job `E2E (Playwright)` passa a integrar o gate de merge.
- Mudanças no `grid` dos gráficos (`chart-option.ts`) exigem atualizar `e2e/fixtures.ts`.
