# Fixtures de teste

Arquivos usados **somente** em testes automatizados. Nunca são carregados pela aplicação.

- `sgs_432_sample.json`: trecho **real** da SGS 432 (meta Selic), copiado da API oficial do BCB
  em 2026-10-21 (`dataInicial=14/09/2026&dataFinal=20/09/2026`), cobrindo a mudança de 14,00 → 13,75
  vigente a partir de 17/09/2026.
- `sgs_html_error.html`: página HTML de "Requisição inválida" devolvida de forma intermitente
  pelo gateway do BCB (trecho reduzido).

Os demais dados usados nos testes são construídos inline e são sintéticos (identificados como tais).
