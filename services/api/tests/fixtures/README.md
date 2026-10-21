# Fixtures de teste

Arquivos usados **somente** em testes automatizados. Nunca são carregados pela aplicação.

- `sgs_432_sample.json`: trecho **real** da SGS 432 (meta Selic), copiado da API oficial do BCB
  em 2026-10-21 (`dataInicial=14/09/2026&dataFinal=20/09/2026`), cobrindo a mudança de 14,00 → 13,75
  vigente a partir de 17/09/2026.
- `sidra_1737_2265_sample.json`: resposta **real** do SIDRA/IBGE (tabela 1737, variável 2265, IPCA
  acumulado em 12 meses), copiada em 2026-10-21 de
  `/values/t/1737/n1/all/v/2265/p/197912,198011,198012,202608,202609/f/c`: cabeçalho, dois meses sem
  valor (`"V": "..."`, `"MC": ""`), o primeiro mês com valor e os dois últimos publicados.
- `sgs_html_error.html`: página HTML de "Requisição inválida" devolvida de forma intermitente
  pelo gateway do BCB (trecho reduzido).

Os demais dados usados nos testes são construídos inline e são sintéticos (identificados como tais).
