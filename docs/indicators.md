# Catálogo de indicadores

| Código interno | Nome | Fonte / série | Unidade | Variação | Frequência | Nível | Início | Status |
|---|---|---|---|---|---|---|---|---|
| `SELIC_TARGET` | Taxa de juros - Meta Selic definida pelo Copom | BCB SGS 432 | % a.a. | p.p. | diária (dias corridos) | Brasil | 05/03/1999 | **Implementado** |
| `IPCA_12M` | IPCA acumulado em 12 meses | IBGE SIDRA, tabela 1737 (variável a confirmar) | % | p.p. | mensal | Brasil | — | Próxima etapa |
| `DBGG_GDP` | Dívida bruta do governo geral (% PIB) - Metodologia utilizada a partir de 2008 | BCB SGS 13762 | % do PIB | p.p. | mensal (posição de fim de mês) | Brasil | 01/12/2006 | **Implementado** |

Indicadores só entram no catálogo (migração de seed) depois que seus metadados são confirmados na
fonte oficial. Por isso `IPCA_12M` ainda não está no banco.

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
