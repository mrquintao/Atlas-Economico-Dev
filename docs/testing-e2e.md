# Testes end-to-end (Playwright)

Testes de navegador do fluxo principal, em `apps/web/e2e/`, executados pelo job **`E2E (Playwright)`**
do CI, que faz parte do gate de merge ([AGENT_POLICY §3](autonomy/AGENT_POLICY.md)). Decisões em
[ADR 0008](adr/0008-testes-e2e-com-dados-sinteticos.md).

## Dados: fixture SINTÉTICA

Os E2E nunca usam dados oficiais coletados nem chamam as fontes. O banco de teste é preenchido por
[`services/api/tests/fixtures/e2e_seed.py`](../services/api/tests/fixtures/e2e_seed.py), com valores
**inventados e determinísticos**, identificados em cada linha (`source_reference =
"synthetic-e2e-fixture"`, `metadata_json = {"synthetic": true}`):

| Indicador | Frequência | Período sintético |
|---|---|---|
| `SELIC_TARGET` | diária | 01/01/2004 a 30/06/2026 (nível que muda a cada 45 dias) |
| `DBGG_GDP` | mensal | dez/2006 a mai/2026 |
| `IPCA_12M` | mensal | jan/2000 a mai/2026 |

O script só roda com `ATLAS_E2E_SEED=1` e recusa bancos que já tenham observações, de modo que nunca
mistura valores sintéticos com dados oficiais. Use sempre um banco descartável.

## O que é verificado

- Painel nacional: cartões e os três gráficos, sem estado de erro.
- Presets (5 anos, 10 anos, desde 2008, todo o histórico) aplicados a **todos** os gráficos, conferidos
  pelo resumo textual (nome acessível) de cada gráfico.
- Cursor sincronizado: um dia do gráfico diário mostra, nos mensais, o **mês que contém o dia**; um mês
  dos gráficos mensais mostra, no diário, o **último dia daquele mês**.
- Zoom sincronizado: depois do zoom em um gráfico, a mesma posição horizontal mostra a mesma data nos
  demais.
- Troca diária/mensal da Selic mantendo o zoom.
- Estado vazio (período sem observações) e intervalo inválido (início após o fim).
- Navegação para "Metodologia" e "Fontes de dados", âncoras por indicador e link do painel de metodologia.
- **Nenhum erro no console** nem exceção não tratada em nenhum teste (fixture automática).

Os testes leem as dicas de contexto (tooltips HTML) do ECharts e os nomes acessíveis dos gráficos; não
há ganchos de teste no código do produto. Cada verificação de sincronização foi conferida por mutação
(quebrar `syncZoom`, `alignTime` ou `afterOptionUpdate` faz o teste correspondente falhar).

## Execução local

```bash
# Banco descartável com a fixture sintética (nunca o banco `atlas` com dados reais)
cd services/api
export DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_e2e
uv run alembic upgrade head
ATLAS_E2E_SEED=1 uv run python -m tests.fixtures.e2e_seed

# O Playwright sobe a API (porta 8000) e o build de produção do site (porta 3000)
cd ../../apps/web
npx playwright install chromium        # uma vez; ou PLAYWRIGHT_CHROMIUM_EXECUTABLE=/caminho/do/chrome
npm run build
npm run test:e2e
```

Fora do CI, servidores já em execução nas portas 3000/8000 são reaproveitados: confira se a API em uso
aponta para o banco sintético. Em caso de falha, `test-results/` guarda captura de tela e trace
(`npx playwright show-trace …`); no CI eles são publicados como artefato `playwright-report`.
