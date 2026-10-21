# ADR 0002 — Regras de dados da meta Selic

**Status:** aceito (2026-10-21) — validado pelo agente `economist`.

1. **Coletar até a data da coleta, no horário de Brasília.** O SGS 432 publica antecipadamente a meta vigente até a próxima
   reunião do Copom. Esses dias não são observações e podem mudar (ex.: reunião extraordinária), então
   não são armazenados. A regra vale no parâmetro `dataFinal` e também como filtro no pipeline.
2. **Janelas de 1 ano** em vez do limite oficial de 10: janelas grandes levam ~30 s e estouram o
   timeout com frequência; janelas de 1 ano respondem em ~1 s. Configurável (`BCB_DAILY_WINDOW_YEARS`).
3. **Visão mensal = último valor do mês**, marcado como parcial quando o mês não está completo.
   Nenhuma média, porque a série é um nível que muda em degraus.
4. **Incremental com sobreposição de 90 dias** para detectar revisões recentes; revisões geram
   registros em `observation_revisions`.
5. **Catálogo só com indicadores verificados:** a spec (§27, passo 5) sugere já criar
   `DBGG_GDP` e `IPCA_12M`; eles entram por migração própria quando seus metadados forem confirmados
   (a spec exige investigar a variável da tabela SIDRA 1737 antes).
