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
| 9 indicadores `STATE_*` | bimestral e quadrimestral | 2023 a 2025: SP com os nove, DF sem `STATE_NOMINAL_RESULT`, MG só com `STATE_RCL` e `STATE_DCL_RCL`; demais UFs sem dados |
| Malha das 27 UFs | edição 2022, `minima` | **quadrados** numa grade (não é a malha do IBGE), `source_url = "synthetic-e2e-fixture"` |

O script só roda com `ATLAS_E2E_SEED=1`, num banco cujo nome contenha `e2e` ou `test` (o banco
`atlas`, padrão do `DATABASE_URL`, é recusado) e que ainda não tenha observações, execuções de coleta
nem malhas.
Assim, nunca mistura valores sintéticos com dados oficiais.

## O que é verificado

- Painel nacional: cartões e os três gráficos, sem estado de erro.
- Presets (5 anos, 10 anos, desde 2008, todo o histórico) aplicados a **todos** os gráficos, conferidos
  pelo resumo textual (nome acessível) de cada gráfico.
- Cursor sincronizado: um dia do gráfico diário mostra, nos mensais, o **mês que contém o dia**; um mês
  dos gráficos mensais mostra, no diário, o **último dia daquele mês**; onde uma série não tem dado
  (junho de 2026 para as mensais), o cursor dela **some** em vez de exibir o mês vizinho.
- Zoom sincronizado: depois do zoom em um gráfico, a mesma posição horizontal mostra a mesma data nos
  demais.
- Troca diária/mensal da Selic mantendo o zoom.
- Estado vazio (período sem observações) e intervalo inválido (início após o fim).
- Páginas estaduais (`e2e/states.spec.ts`): lista das 27 UFs; cartões de SP (valor em reais com
  escala, bimestre/quadrimestre, janela de acumulação, diferença para o mesmo período do ano anterior
  e fonte); gráficos nomeados pelos períodos; cursor de um quadrimestre que destaca o **último
  bimestre** do período no gráfico bimestral; período personalizado; ressalva e indicador ausente do
  DF; ausências explícitas de MG; UF sem dados (AC); `/estados/mg` → `308` para `/estados/MG`; UF
  inválida (`XX`, `BR`, `31`) → página "não encontrada" com status `404`.
- Mapa das UFs (S6, em `e2e/states.spec.ts`): 27 UFs como links nomeados por valor, unidade e
  período; UF sem dado com rótulo "sem dado" e padrão hachurado; legenda com faixas e "Sem dado";
  tabela alternativa; dica de contexto no hover; clique e teclado (foco + Enter) abrem a UF; filtros de
  período e de indicador (período mantido entre indicadores quadrimestrais; escala divergente da DCL/RCL).
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
