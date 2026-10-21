# Metodologias e regras de apresentação

## Regras gerais

1. **Nenhum valor é inventado, estimado ou interpolado.** Datas sem valor oficial não existem no banco;
   valores ausentes na fonte (`""`/`null`) são descartados e contados em `ingestion_runs.metadata_json`,
   nunca convertidos em zero.
2. **Frequência original preservada.** O banco guarda a série como publicada. Qualquer conversão é feita
   na consulta e declarada na resposta (`aggregation.method` e `aggregation.description`).
3. **Variações de taxas em pontos percentuais.** A diferença entre dois valores de um indicador
   em % é expressa em `p.p.` (`indicators.change_unit`). Selic de 10% para 12% = **+2 p.p.**
4. **Gráficos não enganosos.** Eixo vertical começa em zero para taxas; escalas diferentes ficam em
   gráficos separados; nada de eixo duplo indiscriminado.

## Meta Selic (SGS 432)

- Série **diária em dias corridos** (inclusive fins de semana e feriados): cada dia registra a meta
  vigente, que só muda nas decisões do Copom (vale a partir do dia seguinte à reunião).
  Por isso o gráfico usa linha em **degraus**.
- **Datas futuras:** o BCB publica antecipadamente a meta vigente até a próxima reunião do Copom
  (ex.: em 21/10/2026 a API já trazia valores até 04/11/2026). Esses dias **não são armazenados**:
  a coleta usa `dataFinal = data da coleta` (no horário de Brasília) e o pipeline descarta qualquer
  data posterior, por segurança. As coletas diárias incorporam os dias à medida que ocorrem.
- **Visão mensal:** valor vigente no **último dia de cada mês** (último valor disponível no mês),
  sem médias. No mês corrente, ou num mês cortado pela data final escolhida, usa-se o último valor
  disponível e o ponto é marcado como **parcial** (`partial: true`, marcador vazado no gráfico e
  “mês parcial” no tooltip). O mesmo vale para um mês cortado pela data inicial ou pelo início da série.
- **Variação em 12 meses** (cartão): diferença em p.p. entre o último valor disponível e o valor
  do mesmo mês do ano anterior na visão mensal.
