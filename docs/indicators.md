# Catálogo de indicadores

| Código interno | Nome | Fonte / série | Unidade | Variação | Frequência | Nível | Início | Status |
|---|---|---|---|---|---|---|---|---|
| `SELIC_TARGET` | Taxa de juros - Meta Selic definida pelo Copom | BCB SGS 432 | % a.a. | p.p. | diária (dias corridos) | Brasil | 05/03/1999 | **Implementado** |
| `IPCA_12M` | IPCA - Variação acumulada em 12 meses | IBGE SIDRA, tabela 1737, variável 2265 | % | p.p. | mensal (mês de referência) | Brasil | 01/12/1980 | **Implementado** |
| `DBGG_GDP` | Dívida bruta do governo geral (% PIB) - Metodologia utilizada a partir de 2008 | BCB SGS 13762 | % do PIB | p.p. | mensal (posição de fim de mês) | Brasil | 01/12/2006 | **Implementado** |

Indicadores só entram no catálogo (migração de seed) depois que seus metadados são confirmados na
fonte oficial.

## SELIC_TARGET (SGS 432)

- **Link oficial:** https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom
- **Fonte / publicação:** Copom / BCB-Demab. Licença ODbL.
- **Primeira observação:** 05/03/1999 (45,00% a.a.), confirmada consultando a API.
- **Não confundir** com a Selic efetiva (taxa over), séries SGS 11 e 1178.
- **Amostras conferidas na API oficial em 21/10/2026:** 01/01/2008 = 11,25 · 31/12/2015 = 14,25 ·
  31/12/2020 = 2,00 · 31/12/2024 = 12,25 · 17/09/2026 = 13,75 (vigente a partir de 17/09/2026; 16/09 = 14,00).

## DBGG_GDP (SGS 13762)

- **Link oficial:** https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008
- **Fonte:** BCB/Depec (Departamento Econômico), Estatísticas Fiscais. Licença ODbL.
- **Construção (verificada por conta):** SGS 13762 = SGS 13761 (saldo da DBGG, R$ milhões, fim de mês)
  ÷ SGS 4382 (PIB acumulado em 12 meses a preços correntes) × 100. Ex.: ago/2026 =
  11.054.954,37 / 13.340.676,3 = 82,87.
- **Data do SGS:** `01/MM/AAAA` = posição de **fim** do mês MM. O banco guarda `reference_date` = dia 1
  (convenção do SGS) e `period_end` = último dia do mês.
- **Abrangência:** governo federal (com INSS), estados e municípios; inclui as operações compromissadas
  do BCB; exclui empresas estatais; deduz títulos em poder de órgãos e fundos públicos.
- **Primeira observação:** dez/2006 (55,48). Defasagem de divulgação de ~5–7 semanas (inferida).
- **Não confundir** com SGS 4537 (metodologia até 2007, ainda atualizada: 94,54 em ago/2026),
  SGS 13761 (saldo em R$ milhões) ou com a dívida bruta no conceito do FMI.
- **Amostras conferidas na API oficial em 21/10/2026** (economist) e no banco após a coleta:
  dez/2006 = 55,48 · dez/2008 = 55,98 · dez/2013 = 51,54 · dez/2015 = 65,50 · dez/2019 = 74,44 ·
  dez/2020 = 86,94 · dez/2022 = 71,68 · dez/2024 = 76,27 · ago/2025 = 77,31 · ago/2026 = 82,87.

## IPCA_12M (SIDRA 1737, variável 2265)

- **Link oficial:** https://sidra.ibge.gov.br/tabela/1737 · API: `https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/{AAAAMM}-{AAAAMM}/f/c`
- **Fonte:** IBGE, Sistema Nacional de Índices de Preços ao Consumidor (SNIPC). Tabela 1737 = "IPCA - Série
  histórica com número-índice, variação mensal e variações acumuladas em 3 meses, em 6 meses, no ano e
  em 12 meses (a partir de dezembro/1979)".
- **Variável correta:** `2265` = "IPCA - Variação acumulada em 12 meses", unidade `%` (código de unidade
  `2`, validado na coleta). **Não confundir** com `63` (variação mensal), `69` (acumulada no ano),
  `2263`/`2264` (3 e 6 meses) ou `2266` (número-índice, dez/1993 = 100; unidade código `30`).
- **Data:** o código de período `AAAAMM` é o **mês de referência**; o banco guarda `reference_date` =
  dia 1, `period_start`/`period_end` = 1º e último dia do mês de referência (ADR 0005). A janela de
  acumulação (12 meses até o mês de referência) é descrita na metodologia, não no período.
- **Primeira observação:** dez/1980. De dez/1979 a nov/1980 o SIDRA devolve `...` (sem 12 meses de
  histórico); esses meses não são armazenados. Os marcadores `...`, `..`, `-` e `X` são sempre ausência.
- **Divulgação:** mensal, cerca de 10 dias após o fim do mês de referência. Revisões são raras; a série
  inteira (550 pontos) é recoletada a cada execução, numa só requisição.
- **Conferência em 21/10/2026 (IPCA_12M no banco após a coleta real):** dez/1994 = 916,46 ·
  jan/2003 = 14,47 · dez/2015 = 10,67 · dez/2021 = 10,06 · set/2025 = 5,17 · set/2026 = 4,58 (última).
  As 550 observações do banco foram comparadas uma a uma com `p/all` do SIDRA: nenhuma divergência.
  Verificação independente: o acumulado foi recalculado como o produto das 12 variações mensais
  (variável 63) para os 550 meses. A partir de 1996 a diferença máxima é 0,009 ponto, efeito do
  arredondamento das taxas mensais a 2 casas. Nos anos de alta inflação esse arredondamento se
  acumula: a diferença chega a 0,14 ponto em jun/1994 (4.922,60% publicado), menos de 0,004% do valor.
