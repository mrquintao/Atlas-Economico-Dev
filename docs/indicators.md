# Catálogo de indicadores

| Código interno | Nome | Fonte / série | Unidade | Variação | Frequência | Nível | Início | Status |
|---|---|---|---|---|---|---|---|---|
| `SELIC_TARGET` | Taxa de juros - Meta Selic definida pelo Copom | BCB SGS 432 | % a.a. | p.p. | diária (dias corridos) | Brasil | 05/03/1999 | **Implementado** |
| `IPCA_12M` | IPCA acumulado em 12 meses | IBGE SIDRA, tabela 1737 (variável a confirmar) | % | p.p. | mensal | Brasil | — | Próxima etapa |
| `DBGG_GDP` | Dívida Bruta do Governo Geral (% PIB), metodologia a partir de 2008 | BCB SGS 13762 | % do PIB | p.p. | mensal | Brasil | — | Próxima etapa |

Indicadores só entram no catálogo (migração de seed) depois que seus metadados são confirmados na
fonte oficial. Por isso `IPCA_12M` e `DBGG_GDP` ainda não estão no banco.

## SELIC_TARGET (SGS 432)

- **Link oficial:** https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom
- **Fonte / publicação:** Copom / BCB-Demab. Licença ODbL.
- **Primeira observação:** 05/03/1999 (45,00% a.a.), confirmada consultando a API.
- **Não confundir** com a Selic efetiva (taxa over), séries SGS 11 e 1178.
- **Amostras conferidas na API oficial em 21/10/2026:** 01/01/2008 = 11,25 · 31/12/2015 = 14,25 ·
  31/12/2020 = 2,00 · 31/12/2024 = 12,25 · 17/09/2026 = 13,75 (vigente a partir de 17/09/2026; 16/09 = 14,00).
