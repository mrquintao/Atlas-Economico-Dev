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

## Dívida bruta do governo geral / PIB (SGS 13762)

- Série **mensal**: cada ponto é a posição de fim de mês da dívida bruta dividida pelo PIB acumulado
  nos 12 meses até aquele mês, a preços correntes. Exibida sem transformação (`aggregation: none`);
  o gráfico usa linha contínua (não degraus), e o tooltip mostra apenas o mês de referência.
- **Revisões:** nos meses recentes o PIB do denominador é estimado pelo BCB e é substituído quando o
  IBGE publica as Contas Nacionais; revisões do PIB podem alcançar anos anteriores. Por isso a série
  inteira (~240 pontos, uma requisição) é **recoletada a cada atualização**, e toda mudança de valor
  fica registrada em `observation_revisions`.
- **Integridade:** não emendar com a série da metodologia até 2007 (SGS 4537) nem comparar com a
  dívida bruta do FMI — são conceitos diferentes.
- **Variações** em pontos percentuais do PIB (ex.: ago/2025 → ago/2026: 77,31 → 82,87 = +5,56 p.p.).

## Painel com vários indicadores

- Um **único período** (filtro global) vale para todos os gráficos, que compartilham o mesmo domínio
  do eixo de datas e a mesma área de plotagem: uma data fica na mesma posição horizontal em todos.
- **Zoom e cursor sincronizados por data** (não por índice): ao apontar um dia no gráfico diário, o
  gráfico mensal destaca o ponto mensal existente mais próximo — nada é interpolado.
- Cada indicador mantém sua frequência e unidade; escalas diferentes ficam em gráficos separados.
- Séries mensais são filtradas pela data de referência do SGS (dia 1 do mês): um período iniciado
  em 20/10/2021 começa no ponto de nov/2021.
