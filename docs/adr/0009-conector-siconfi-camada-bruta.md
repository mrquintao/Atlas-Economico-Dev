# ADR 0009 — Conector SICONFI e camada bruta de relatórios fiscais

**Status:** aceito (2026-10-21), issue #13 (S3).

## Contexto

A fase 2 depende dos relatórios fiscais que os estados entregam ao SICONFI (RREO bimestral,
consolidado do ente; RGF quadrimestral, um por Poder ou órgão — LRF arts. 52, 54 e 55). A API de dados abertos do Tesouro (`apidatalake.tesouro.gov.br/ords/siconfi/tt`) serve
cada anexo como linhas (`rotulo`, `coluna`, `conta`, `valor`), paginadas (ORDS, até 5000 por página), com
limite documentado de 1 requisição por segundo. Os indicadores estaduais (RCL, DCL, DCL/RCL, despesa
com pessoal, resultados primário e nominal) ainda serão definidos e validados pelo economist na S4;
cada um depende de linhas e colunas específicas de anexos diferentes, e as estruturas dos anexos mudam
entre exercícios.

## Decisões

1. **Camada bruta separada do catálogo.** Os anexos são gravados como publicados em
   `fiscal_reports` + `fiscal_report_rows`, e não em `observations`. Assim a escolha das linhas que
   formam cada indicador (S4) pode ser revista e reprocessada sem nova coleta, e cada número exibido
   no futuro pode ser rastreado até a linha oficial do anexo. Alternativa descartada: JSONB com o
   payload inteiro, que não permite consultar linhas nem detectar revisões por valor.
2. **Coleta incremental guiada pelo `extrato_entregas`.** Uma requisição por UF e ano diz quais
   períodos foram entregues e quando foram entregues ou retificados; só esses anexos são pedidos.
   Coletar 27 UFs × 6 bimestres sem o extrato custaria 162 requisições (≈ 3 min) por anexo e ano; com
   ele, uma recoleta sem novidades custa 27. A data mais recente entre todos os órgãos do ente é usada
   (conservador: no RGF cada poder entrega o seu relatório e não é preciso casar nomes de órgãos).
3. **Revisões.** `content_hash` canônico por anexo; numa retificação as linhas são atualizadas,
   inseridas ou removidas para espelhar a fonte, e cada mudança (valor anterior e novo) fica em
   `ingestion_runs.metadata_json.revisions`. Os indicadores derivados (S4) terão o histórico de revisões
   próprio de `observation_revisions`.
4. **Limite de taxa inviolável pela configuração.** `SICONFI_MIN_REQUEST_INTERVAL_SECONDS` tem padrão
   1,1 s e mínimo 1,0 s; o limitador vale para todas as requisições (páginas e novas tentativas) e
   recebe relógio injetável para ser testado de forma determinística.
5. **Valores exatos.** O JSON é lido com `parse_float=Decimal`; nenhum valor passa por `float`.
6. **Coleta manual por enquanto.** O agendador (ADR 0007) não coleta o SICONFI até a S4 definir os
   anexos e o calendário de entregas que alimentam indicadores.

## Consequências

- Uma UF sem entrega aparece como `not_delivered`; entrega ainda ausente do data lake, como
  `not_available` — nenhuma das duas é gravada como zero ou lacuna preenchida.
- O RREO é consolidado do ente (`power` nulo); a unicidade usa `NULLS NOT DISTINCT` (PostgreSQL ≥ 15;
  o projeto usa 16).
- O RGF é gravado por poder. Os anexos de dívida, garantias e operações de crédito (02, 03 e 04) só são
  publicados pelo Executivo e já se referem ao ente inteiro. O anexo de pessoal (01) é por Poder ou
  órgão, e o total do ente não é a soma automática dos RGFs: o limite de 60% da RCL (LRF art. 19) e os
  sublimites por poder (art. 20) têm de ser lidos do demonstrativo consolidado ou definidos
  explicitamente na S4.
- Pontos para a S4 (economist): identificar linhas por `cod_conta` e coluna, nunca por posição; as
  estruturas dos anexos mudam entre edições do MDF (ex.: resultados primário e nominal por volta de
  2017/2018; ajustes da RCL pela EC 109/2021 e LC 178/2021); colunas do Anexo 02 são saldos, as do RREO
  são fluxos acumulados; as linhas do DF (`id_ente=53`) voltam com `esfera = "E"` (conferido em 21/10/2026, RREO-Anexo 03 de 2024).
- A fonte `SICONFI` aparece em `/fontes` sem indicadores até a S4.
