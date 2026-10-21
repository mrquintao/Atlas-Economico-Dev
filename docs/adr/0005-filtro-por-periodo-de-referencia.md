# ADR 0005 — Filtro temporal por período de referência e parâmetros desconhecidos

**Status:** aceito (2026-10-21). Issue #3 (M1).

## Contexto

1. Séries mensais do SGS são datadas no dia 1 do mês, mas representam o mês inteiro (ex.: DBGG/PIB é a
   posição de fim de mês). Filtrar por essa data excluía o primeiro mês de um intervalo iniciado no meio
   do mês: com início em 20/10/2021, out/2021 sumia, embora sua posição de fim de mês esteja no intervalo.
2. A API ignorava parâmetros desconhecidos: `?start=2030-01-01` (erro de digitação de `start_date`)
   devolvia a série inteira, com cara de resposta filtrada válida.

## Decisões

1. **Sobreposição de períodos:** uma observação entra quando `period_end >= start_date` e
   `period_start <= end_date`. Para séries diárias (período = o próprio dia) o resultado é idêntico ao
   filtro anterior. O `start_date` efetivo da resposta nunca é anterior ao pedido.
2. **Presets relativos alinhados ao mês:** "5 anos" e "10 anos" começam no dia 1 do mês, de modo que
   todas as séries do painel mostram meses completos e equivalentes.
3. **Domínio do eixo X** começa no dia 1 do mês da data inicial, para que o ponto mensal incluído pela
   sobreposição fique visível. Num intervalo personalizado iniciado no meio do mês, o gráfico diário mostra
   o trecho do mês anterior ao início sem dados (fora do período pedido), e não com valores inventados.
4. **Parâmetros desconhecidos → `422 unknown_parameter`**, aplicado no roteador `/api/v1` por uma
   dependência que compara a query string com os parâmetros que a rota (e suas dependências) declaram.
   Vale automaticamente para rotas futuras, sem lista manual.
