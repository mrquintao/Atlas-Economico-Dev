# ADR 0005 — Filtro temporal pelo fim do período de referência e parâmetros desconhecidos

**Status:** aceito (2026-10-21), issue #3 (M1). A regra de filtro foi validada pelo agente `economist`.
Uma primeira versão desta decisão (sobreposição de períodos) foi substituída antes do merge, depois da
auditoria do `qa-auditor`.

## Contexto

1. Séries mensais do SGS são datadas no dia 1, mas representam o mês inteiro. Na DBGG/PIB, por exemplo,
   o valor é a posição de **fim** de mês. Filtrar pela data do dia 1 excluía out/2021 de um intervalo
   iniciado em 20/10/2021, embora a posição de 31/10 esteja dentro dele. Filtrar por sobreposição
   resolvia o início, mas incluía mar/2022 num intervalo encerrado em 15/03/2022, ou seja, um valor
   referente a um momento posterior ao fim pedido.
2. A API ignorava parâmetros desconhecidos: `?start=2030-01-01` (erro de digitação de `start_date`)
   devolvia a série inteira, com cara de resposta filtrada válida. Parâmetros repetidos usavam o último valor.

## Decisões

1. **Uma observação entra quando seu período de referência termina dentro do intervalo:**
   `start_date <= period_end <= end_date`. É a mesma regra para todos os tipos de série:
   - diárias (período = o dia): equivale ao filtro por data;
   - estoques (DBGG/PIB): inclui exatamente as posições cujo instante está no intervalo;
   - acumulados (IPCA em 12 meses, fiscais acumulados no ano, futuros): o critério é o mês de referência
     (fim da janela); a janela da medida pode começar antes do início escolhido, por definição.

   Para isso, `period_start`/`period_end` são sempre o período de referência (mês ou bimestre), nunca a
   janela de acumulação, que é metadado da série. Um intervalo contido num único mês não traz ponto
   mensal: a interface mostra o estado vazio, nunca um valor preenchido.
2. **Datas efetivas da resposta:** `start_date` e `end_date` descrevem o intervalo coberto pelos
   períodos devolvidos, recortado ao pedido: início do primeiro período (ou o início pedido, se
   posterior) até o fim do último período (ou a última data disponível, se o período estiver parcial).
3. **Índice** `(indicator_id, geographic_unit_id, period_end)` (migração 0004) atende ao filtro.
4. **Presets relativos alinhados ao mês:** "5 anos" e "10 anos" começam no dia 1 do mês.
5. **Posição no gráfico e domínio do eixo X:** cada ponto é desenhado na data de referência
   do SGS (dia 1 do mês nas séries mensais; o tooltip mostra o mês, "Referência: mês/ano"). O domínio
   começa no dia 1 do mês da data inicial, para que o ponto mensal incluído fique visível.
6. **Parâmetros de consulta:** dependência no roteador `/api/v1` compara a query string com os
   parâmetros declarados pela rota e suas dependências (inclusive campos de modelos Pydantic declarados
   como query). Desconhecidos geram `422 unknown_parameter`; um parâmetro escalar repetido gera
   `422 repeated_parameter`. A validação ocorre antes do tratamento da rota, então um indicador inexistente
   com parâmetro desconhecido responde 422 (e não 404).
