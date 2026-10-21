# Fixtures de teste

Arquivos usados **somente** em testes automatizados. Nunca são carregados pela aplicação.

- `sgs_432_sample.json`: trecho **real** da SGS 432 (meta Selic), copiado da API oficial do BCB
  em 2026-10-21 (`dataInicial=14/09/2026&dataFinal=20/09/2026`), cobrindo a mudança de 14,00 → 13,75
  vigente a partir de 17/09/2026.
- `sidra_1737_2265_sample.json`: resposta **real** do SIDRA/IBGE (tabela 1737, variável 2265, IPCA
  acumulado em 12 meses), copiada em 2026-10-21 de
  `/values/t/1737/n1/all/v/2265/p/197912,198011,198012,202608,202609/f/c`: cabeçalho, dois meses sem
  valor (`"V": "..."`, `"MC": ""`), o primeiro mês com valor e os dois últimos publicados.
- `ibge_malhas_uf_2022_minima_sample.json`: trecho **real** da API de malhas do IBGE, copiado em
  2026-10-21 de `/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima&periodo=2022`,
  reduzido às feições de Amapá (`16`, MultiPolygon), Sergipe (`28`) e Distrito Federal (`53`), sem
  alteração das geometrias.
- `siconfi_rgf_anexo02_sp_2024_q3_sample.json`, `siconfi_rreo_anexo03_sp_2024_b6_sample.json` e
  `siconfi_extrato_sp_2024_sample.json`: trechos **reais** da API do SICONFI, copiados em 2026-10-21 de
  `/tt/rgf?an_exercicio=2024&in_periodicidade=Q&nr_periodo=3&co_tipo_demonstrativo=RGF&no_anexo=RGF-Anexo 02&co_esfera=E&co_poder=E&id_ente=35`
  (6 linhas da dívida consolidada e da DCL), `/tt/rreo?an_exercicio=2024&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo 03&co_esfera=E&id_ente=35`
  (4 primeiras linhas) e `/tt/extrato_entregas?id_ente=35&an_referencia=2024` (entregas do RREO, do RGF
  do Executivo e do Tribunal de Justiça e da MSC de janeiro). Valores e textos sem alteração; `count` e
  `links` ajustados ao trecho.
- `sgs_html_error.html`: página HTML de "Requisição inválida" devolvida de forma intermitente
  pelo gateway do BCB (trecho reduzido).

- `e2e_seed.py`: **dados SINTÉTICOS** (inventados e determinísticos) para os testes de navegador
  (`apps/web/e2e`). Carregados só por `ATLAS_E2E_SEED=1 python -m tests.fixtures.e2e_seed` num banco
  descartável e vazio, cujo nome contenha `e2e` ou `test`; cada linha leva `source_reference = "synthetic-e2e-fixture"`. Ver
  `docs/testing-e2e.md`.

Os demais dados usados nos testes são construídos inline e são sintéticos (identificados como tais).
