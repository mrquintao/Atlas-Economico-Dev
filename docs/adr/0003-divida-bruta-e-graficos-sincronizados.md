# ADR 0003 — Dívida bruta/PIB e gráficos sincronizados

**Status:** aceito (2026-10-21). Metadados validados pelo agente `economist`.

## Contexto

Segunda série do MVP: DBGG em % do PIB (SGS 13762), mensal. O PROJECT_SPEC (§5) pede que os gráficos
fiquem sincronizados no tempo e que a frequência original de cada série seja preservada.

## Decisões

1. **Recoleta integral das séries mensais** a cada execução. A razão herda revisões do PIB (estimativa
   do BCB substituída pelas Contas Nacionais do IBGE) que podem alcançar anos para trás; a série inteira
   é uma requisição de ~240 pontos. As mudanças viram `observation_revisions`.
2. **Período de referência mensal** = dia 1 (convenção de data do SGS) até o último dia do mês; datas
   mensais fora do dia 1 são rejeitadas na ingestão.
3. **Período global** para todos os gráficos; a alternância diária/mensal existe só para séries diárias
   (Selic). Séries mensais nunca são convertidas para diárias (`422 frequency_not_supported`).
4. **Sincronização por data, não por índice.** Os gráficos compartilham o domínio do eixo X (início do
   período ou primeira data armazenada → fim do período ou última data armazenada) e uma área de
   plotagem com margens fixas. Cursor e zoom são propagados por data entre as instâncias do ECharts;
   `echarts.connect` foi descartado porque casa tooltips por índice de dado (falha entre séries de
   tamanhos diferentes) e, combinado à propagação manual, gerava recursão infinita.
5. **Sem interpolação no cursor:** o gráfico mensal destaca o ponto mensal existente mais próximo do dia
   apontado no gráfico diário.
