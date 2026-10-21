# ADR 0006 — Conector IBGE/SIDRA e IPCA acumulado em 12 meses

**Status:** aceito (2026-10-21), issue #4 (M2).

## Contexto

O terceiro indicador do MVP é a inflação em 12 meses medida pelo IPCA, publicada pelo IBGE no SIDRA
(tabela 1737). A tabela traz seis variáveis com o mesmo assunto (variação mensal, acumuladas em 3, 6 e
12 meses, no ano, e o número-índice), e trocar uma pela outra produziria números plausíveis e errados.
A ingestão existente era específica do SGS do BCB.

## Decisões

1. **Variável 2265** ("IPCA - Variação acumulada em 12 meses"), nível Brasil (`n1`), confirmada na API
   oficial. O conector valida, em cada linha, a variável (`D2C`) e a unidade (`MC = 2`, %): uma
   variável ou unidade diferente aborta a coleta.
2. **Conector próprio** em `app/integrations/ibge/sidra.py`, com a mesma interface de `fetch_series` do
   conector SGS (retry com backoff, timeout, rate limit, SHA-256 do payload). `source_series_code` guarda
   `tabela/variável` (`1737/2265`).
3. **Ingestão genérica** (`app/ingestion/series_ingestion.py`): idempotência, revisões, `ingestion_runs`
   e período de referência compartilhados; o despacho é pela fonte (`data_sources.acronym`), e a função
   recusa um indicador de outra fonte.
4. **Datas:** o mês de referência define `reference_date`, `period_start` e `period_end` (ADR 0005); a
   janela de acumulação fica na metodologia.
5. **Ausências:** `...`, `..`, `-` e `X` são ausência, nunca zero. Antes de dez/1980 não há acumulado em
   12 meses; `first_available_date` = 1980-12-01.
6. **Coleta integral** a cada execução (550 pontos numa requisição), como nas demais séries mensais, para
   capturar eventuais revisões.
7. **Lacunas no gráfico:** períodos ausentes entre duas observações viram uma quebra explícita na linha,
   em qualquer série.

## Consequências

- Novas séries do SIDRA entram por migração de seed, sem código novo, desde que sejam mensais e
  nacionais. Outras periodicidades ou níveis territoriais exigirão estender o conector.
- A unidade validada (`%`) é fixa no conector; um indicador do SIDRA em outra unidade precisará
  parametrizá-la.
