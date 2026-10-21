# Metodologias e regras de apresentação

## Regras gerais

1. **Nenhum valor é inventado, estimado ou interpolado.** Datas sem valor oficial não existem no banco;
   valores ausentes na fonte (`""`/`null`) são descartados e contados em `ingestion_runs.metadata_json`,
   nunca convertidos em zero.
2. **Frequência original preservada.** O banco guarda a série como publicada. Qualquer conversão é feita
   na consulta e declarada na resposta (`aggregation.method` e `aggregation.description`).
3. **Variações de taxas em pontos percentuais.** A diferença entre dois valores de um indicador
   em % é expressa em `p.p.` (`indicators.change_unit`). Selic de 10% para 12% = **+2 p.p.**
4. **Gráficos não enganosos.** Eixo vertical começa em zero para taxas (ou abaixo de zero, só quando a série tem valores negativos); escalas diferentes ficam em
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

## IPCA acumulado em 12 meses (SIDRA 1737, variável 2265)

- Série **mensal**: cada ponto é a variação do IPCA nos 12 meses encerrados no **mês de referência**
  (produto das 12 variações mensais). A data do ponto é o mês de referência; a janela de acumulação
  começa 11 meses antes. Ao filtrar um período, o primeiro ponto mostrado pode, portanto, refletir
  preços de meses anteriores ao início escolhido (ADR 0005).
- Exibida sem transformação (`aggregation: none`), em linha contínua; o cartão mostra
  "Referência: mês/ano".
- **Não é** a variação mensal nem a acumulada no ano, que são outras variáveis da mesma tabela.
- **Variações** em pontos percentuais (ex.: set/2025 → set/2026: 5,17% → 4,58% = −0,59 p.p.).
- **Escala:** o histórico inclui a hiperinflação (máxima de 6.821,31% em abr/1990). O período padrão
  do painel (desde 2008) não é afetado; períodos que incluem os anos 1980–1994 comprimem visualmente
  os valores recentes. O menor valor da série é 1,65% (dez/1998); não há valores negativos até set/2026.

## Lacunas nos gráficos

Quando falta um período entre duas observações (um dia numa série diária, um mês numa mensal), o
gráfico insere uma quebra explícita: a linha é interrompida, nunca ligada por cima da ausência.

## Painel com vários indicadores

- Um **único período** (filtro global) vale para todos os gráficos, que compartilham o mesmo domínio
  do eixo de datas e a mesma área de plotagem: uma data fica na mesma posição horizontal em todos.
- **Zoom e cursor sincronizados por data** (não por índice): ao apontar um dia no gráfico diário, o
  gráfico mensal destaca o **mês que contém** aquele dia (27/03/2023 → mar/2023, nunca o mês mais
  próximo); ao apontar um mês, o gráfico diário mostra o último dia desse mês. Nada é interpolado.
- O zoom é mantido quando um gráfico é redesenhado (ex.: troca diária/mensal) e volta ao período
  inteiro quando o período global muda.
- Cada indicador mantém sua frequência e unidade; escalas diferentes ficam em gráficos separados.
- **Filtro por período de referência:** cada observação entra no período escolhido quando o seu
  período de referência termina dentro dele: o próprio dia, para séries diárias; o último dia do mês
  (ou bimestre, quadrimestre), para as demais. Assim, um intervalo de 20/10/2021 a 15/03/2022 inclui
  out/2021 (encerrado em 31/10) e não inclui mar/2022 (encerrado depois de 15/03). Para indicadores
  acumulados, como o IPCA em 12 meses, o valor vale para a janela que termina no mês de referência, e
  essa janela pode começar antes do início do período escolhido. Os presets relativos começam no
  1º dia do mês ([ADR 0005](adr/0005-filtro-por-periodo-de-referencia.md)).
