# Indicadores fiscais estaduais (S4)

Indicadores dos estados e do Distrito Federal derivados dos relatórios entregues ao SICONFI (Tesouro
Nacional). Cada indicador é **uma linha publicada** de um anexo, identificada por código de conta
(`cod_conta`) e coluna, nunca por posição; nada é recalculado pelo Atlas. Decisões técnicas no
[ADR 0010](adr/0010-indicadores-fiscais-estaduais.md); coleta e derivação em
[`data-pipeline.md`](data-pipeline.md).

## Mapeamento

| Código | Relatório / anexo | Poder | `cod_conta` | Coluna | Exercícios | Unidade | Janela | Sinal |
|---|---|---|---|---|---|---|---|---|
| `STATE_RCL` | RREO, Anexo 03 | — | `RREO3ReceitaCorrenteLiquida` | `TOTAL (ÚLTIMOS 12 MESES)` | 2018+ | R$ correntes | 12 meses até o bimestre | ≥ 0 |
| `STATE_DC` | RGF, Anexo 02 | Executivo | `DividaConsolidada` | `Até o {n}º Quadrimestre` | 2018+ | R$ correntes | saldo no fim do quadrimestre | ≥ 0 |
| `STATE_DCL` | RGF, Anexo 02 | Executivo | `DividaConsolidadaLiquida` | `Até o {n}º Quadrimestre` | 2018+ | R$ correntes | saldo | ± |
| `STATE_DCL_RCL` | RGF, Anexo 02 | Executivo | `PercentualDaDCLSobreARCL` | `Até o {n}º Quadrimestre` | 2020+ | % da RCL ajustada (p.p.) | saldo / RCL de 12 meses | ± |
| `STATE_PERSONNEL_EXEC` | RGF, Anexo 01 | Executivo | `DespesaComPessoalTotal` | `Valor` | 2018+ | R$ correntes | 12 meses até o quadrimestre | ≥ 0 |
| `STATE_PERSONNEL_EXEC_RCL` | RGF, Anexo 01 | Executivo | `DespesaComPessoalTotal` | `% sobre a RCL Ajustada` | 2018+ | % da RCL ajustada (p.p.) | 12 meses | ≥ 0 |
| `STATE_PRIMARY_RESULT` | RREO, Anexo 06 | — | `ResultadoPrimarioSemRPPSAcimaDaLinha` | `VALOR` | 2023+ | R$ correntes | acumulado no ano até o bimestre | ± (déficit < 0) |
| `STATE_NOMINAL_RESULT` | RREO, Anexo 06 | — | `ResultadoNominalAcimaDaLinhaSemRPPS` | `VALOR` | 2023+ | R$ correntes | acumulado no ano até o bimestre | ± (déficit < 0) |
| `STATE_INVESTMENTS` | RREO, Anexo 01 | — | `Investimentos` | `DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)` | 2018+ | R$ correntes | acumulado no ano até o bimestre | ≥ 0 |

- Frequência: RREO bimestral (`bimonthly`), RGF quadrimestral (`four_monthly`). Período de referência
  = bimestre ou quadrimestre (ADR 0005); a janela de acumulação está na metodologia de cada indicador.
- No RGF, a coluna do quadrimestre *n* é lida só do relatório do período *n*; colunas de períodos
  anteriores e `SALDO DO EXERCÍCIO ANTERIOR` são ignoradas.
- Valores acumulados no ano recomeçam em janeiro: bimestres diferentes não são comparáveis.
- Valores em reais correntes, sem correção pela inflação (correção é a entrega A2).
- Os textos de metodologia exibidos no site estão na migração `0009` e são servidos por `GET /indicators`.

## Parecer do economist (21/10/2026)

**Conclusão: aprovado, com as delimitações abaixo.** As linhas foram identificadas por código de conta
e coluna e conferidas na [API de dados abertos do Tesouro](https://apidatalake.tesouro.gov.br/docs/siconfi/)
para SP, MG, RJ, RS, BA e DF (e ES, MT, AP, PA, RR e PR em pontos específicos), nos exercícios de 2015
a 2026, em cerca de 130 requisições espaçadas de pelo menos 1,2 s.

1. **RCL** (Anexo 3 do RREO, total de 12 meses): estável desde 2018 (até 2017 o código era
   `ReceitaCorrenteLiquida`; mesmo conceito, deixado fora para que as séries comecem juntas). O valor
   coincide com a RCL do Anexo 2 do RGF no mesmo fim de período (SP, 2025: 266.221.395.322,55). Exibe-se
   a RCL da LRF (art. 2º, IV); as RCL ajustadas existem apenas para o cálculo de limites e entram somente
   nos percentuais publicados (diferença de −0,08% em SP e −0,18% na BA em 2025).
2. **Dívida consolidada e DCL** (Anexo 2 do RGF): saldos no fim de cada quadrimestre, publicados apenas
   pelo Executivo e referentes ao estado inteiro. A DCL pode ser negativa (2025: ES −14,7 bi, MT −5,5 bi,
   AP −0,8 bi), quando os haveres financeiros superam a dívida.
3. **DCL/RCL**: percentual exibido como publicado, sem recálculo. Desde 2020 o denominador é a RCL
   ajustada para endividamento; até 2019, a RCL. Para não misturar definições, o Atlas começa a série
   em 2020. Conferência aritmética: 330.471.301.118,90 ÷ 266.021.234.077,37 = 124,23% (SP, 2025, igual
   ao publicado); MG 167,46%; RJ 217,25%.
4. **Despesa com pessoal**: apenas o Poder Executivo (Anexo 1 do RGF do Executivo), em R$ e em % da RCL
   ajustada, como publicados (SP 2025: 109.727.119.797,17 ÷ 265.761.362.580,37 = 41,29%). Não se somam os
   relatórios dos demais Poderes. O limite do Executivo não é sempre 49% (a BA publica 48,6%) e deve ser
   lido do próprio demonstrativo quando exibido. No 3º quadrimestre a despesa inclui os restos a pagar não
   processados inscritos.
5. **Resultados primário e nominal**: metodologia "acima da linha", **sem RPPS**, acumulados no ano até o
   bimestre (Anexo 6 do RREO), **somente a partir de 2023**. A 13ª edição do Manual de Demonstrativos
   Fiscais separou as receitas e despesas do RPPS; antes de 2023 a linha incluía o RPPS e, antes de 2018,
   seguia outro critério (despesa liquidada em vez de paga). Emendar essas séries misturaria conceitos: no
   RJ, em 2023, o resultado com RPPS foi de R$ 1,7 bilhão e o sem RPPS, de R$ 24,9 bilhões. Convenção:
   positivo = superávit, negativo = déficit, conferida pela fórmula do próprio anexo (DCL de 31/12/2024
   menos DCL atual de SP = −12.815.724.429,19 = resultado nominal abaixo da linha sem RPPS). Usa-se "acima
   da linha" porque o "ajustado abaixo da linha" nem sempre coincide (BA 2025: −1,86 bi × −3,11 bi).
6. **Investimentos**: despesas liquidadas do grupo 4, exceto intraorçamentárias (para não contar duas
   vezes transferências dentro do próprio ente), acumuladas no ano (Anexo 1 do RREO). No 6º bimestre,
   valores empenhados e não liquidados vão para restos a pagar não processados e não são somados, para
   manter a mesma definição em todos os bimestres (RS 2025: RPNP de 3,02 bi × liquidados de 2,34 bi).

**Ressalvas.** Fluxos acumulados no ano recomeçam em janeiro. O DF acumula competências estaduais e
municipais (IPTU, ISS e cota-parte do FPM entram na RCL) e não tem Judiciário nem Ministério Público
próprios, o que limita comparações diretas com os estados e deve ser dito sempre que o DF aparecer em
comparações. Lacunas de entrega são lacunas, nunca zero. Nenhuma variação é atribuída a governos ou
eventos. A afirmação de que o MDF (13ª ed.) afere a meta pelo resultado sem RPPS foi confirmada em
documentos de entes que citam o manual ([SEEC-DF, Quadro VII](https://www.economia.df.gov.br/documents/d/seec/q7-quadro-vii-demonstrativo-do-criterio-utilizado-na-apuracao-do-resultado-primario-e-nominal);
[RJ, Anexo 14 do RREO, 6º bim./2023](https://portal.fazenda.rj.gov.br/contabilidade/wp-content/uploads/sites/25/2024/01/Anexo-14_6oBim_RREO_-2023_MDF-13aEd.-Atuarial.pdf));
a escolha da linha sem RPPS não depende dela, porque é a única série consistente a partir de 2023.

**Cuidados de implementação adotados.** Igualdade exata de `cod_conta` (`RREO3ReceitaCorrenteLiquida` é
prefixo de duas RCL ajustadas; `DividaConsolidada`, de `DividaConsolidadaLiquida`); `rotulo` não é usado
("Padrão" desde 2017, nulo antes); linha ausente ou repetida nunca cai para outra linha.

## Amostras oficiais (2025: 6º bimestre do RREO e 3º quadrimestre do RGF do Executivo)

Valores exatamente como publicados, conferidos pelo economist na API em 21/10/2026. São as mesmas
amostras do teste de regressão `tests/test_fiscal_indicators.py`, que usa os anexos oficiais filtrados
em `tests/fixtures/siconfi_official_2025.json`.

| Indicador | SP | MG | RJ | RS | BA | DF |
|---|---|---|---|---|---|---|
| RCL | 266.221.395.322,55 | 111.739.462.561,63 | 100.556.162.133,43 | 65.232.845.641,12 | 68.995.621.759,51 | 39.201.192.140,12 |
| DC | 382.603.718.968,85 | 213.515.242.948,53 | 237.303.359.171,90 | 134.105.266.266,76 | 34.741.201.081,59 | 9.386.032.883,67 |
| DCL | 330.471.301.118,90 | 187.101.497.500,28 | 218.405.063.161,58 | 113.377.582.604,03 | 24.569.330.296,45 | 6.221.218.399,07 |
| DCL/RCL (%) | 124,23 | 167,46 | 217,25 | 174,03 | 35,67 | 15,91 |
| Pessoal do Executivo | 109.727.119.797,17 | 53.869.167.715,23 | 45.958.926.684,55 | 28.739.368.022,57 | 27.772.068.635,09 | 16.175.614.683,65 |
| Pessoal do Executivo / RCL (%) | 41,29 | 48,22 | 45,74 | 44,16 | 40,36 | 41,46 |
| Resultado primário | 8.486.487.348,83 | 4.765.083.530,93 | 793.967.578,97 | −1.989.477.217,56 | −1.450.985.435,85 | −821.469.255,49 |
| Resultado nominal | −23.923.863.520,54 | −10.581.335.263,83 | −20.562.297.949,86 | −3.163.203.504,66 | −1.862.245.134,01 | −808.841.030,57 |
| Investimentos | 11.829.883.529,00 | 6.563.089.695,22 | 5.409.391.134,07 | 2.341.594.679,44 | 7.369.038.232,51 | 1.833.483.393,14 |

Outras amostras conferidas: SP 2026, 2º quadrimestre: DC 390.041.766.345,85, DCL 315.908.470.847,25,
DCL/RCL 113,03%, pessoal 118.023.183.648,21 (42,28%); SP 2026, 4º bimestre: RCL 279.658.527.567,42,
primário 5.320.559.240,55, nominal −3.239.892.643,59, investimentos 6.364.385.612,14; SP 2018, 3º
quadrimestre: DC 311.794.212.065,99; PR 2018, 3º quadrimestre: pessoal 16.756.448.040,19 (44,57%).

## Verificação real (21/10/2026)

- `derive-fiscal --year 2025 --collect` no banco local: 5 anexos × 27 UFs (RGF Anexos 01 e 02 do
  Executivo, 3 quadrimestres; RREO Anexos 01, 03 e 06, 6 bimestres; todas as entregas presentes),
  **1.053 observações** (162 por indicador bimestral, 81 por quadrimestral), 0 `row_missing`,
  0 `ambiguous`. Reexecução: 0 inseridas, 0 alteradas, 1.053 inalteradas.
- As 54 amostras da tabela acima (6 UFs × 9 indicadores) conferem com o banco, sem divergência.
- Conferência independente na API oficial, em períodos do início e do meio do ano de outras UFs:
  RCL PA 2º bim. = 41.267.835.625,04; DCL GO 2º quadr. = 12.520.638.489,13; primário CE 3º bim. =
  858.276.624,42; pessoal/RCL AM 1º quadr. = 38,28%; investimentos SC 4º bim. = 2.858.129.884,70 —
  todos iguais aos derivados. O qa-auditor conferiu ainda AC (DCL, 1º quadr.), TO (DCL/RCL, 1º a 3º
  quadr.) e PE (investimentos, 3º bim.) na camada bruta.

## Mapa das UFs (S6, parecer do economist de 21/10/2026)

O mapa de `/estados` (endpoint `GET /api/v1/states/map/{code}`, contrato em [`api.md`](api.md)) segue
estas regras:

- **Um período para todas as UFs.** O mapa mostra o mesmo bimestre (RREO) ou quadrimestre (RGF) para
  as 27 UFs; nunca o último valor de cada uma. UF sem valor no período = "sem dado", em cinza hachurado,
  fora da paleta, com item próprio na legenda: ausência não é zero.
- **Período padrão**: o mais recente com valor de pelo menos 14 das 27 UFs (os relatórios chegam aos
  poucos); se nenhum atingir esse número, o mais recente com algum valor. Cada período do filtro mostra
  quantas UFs publicaram (`coverage`). Ao trocar de indicador, o período é mantido se for do mesmo tipo
  (quadrimestre × bimestre) e estiver no intervalo armazenado do novo indicador; senão, vale o padrão.
- **Escala**: indicadores nunca negativos (RCL, DC, pessoal em R$ e em % da RCL, investimentos) usam até
  5 classes por **quantis** (posição), paleta sequencial viridis; intervalos iguais não servem (SP
  achataria as outras UFs numa só classe). Indicadores com sinal (resultados primário e nominal, DCL,
  DCL/RCL) usam paleta divergente PuOr: zero é sempre limite de classe e cada lado tem até 3 classes por
  quantis (menos quando há poucas UFs daquele lado). Sem vermelho/verde ("bom/ruim"). O tipo de escala
  é propriedade do catálogo (`SIGNED_CODES`), nunca dos valores do período. Valores iguais ficam sempre
  na mesma classe, e a legenda mostra o intervalo real de cada faixa e quantas UFs ela tem. Um valor
  exatamente zero entra na primeira classe não negativa.
- **Valores absolutos em R$** entram no mapa com a nota "refletem também o tamanho de cada UF"; métricas
  relativas (per capita, rankings) ficam para a S8. Indicador padrão: pessoal do Executivo / RCL (razão,
  desde 2018, nunca negativa).
- **DF** entra na classificação, com asterisco no mapa e na tabela e a nota de comparabilidade.
- **Acumulados no ano**: comparar UFs no mesmo bimestre é coerente; comparar bimestres diferentes não.
  Primário e nominal só têm períodos desde 2023; DCL/RCL, desde 2020. No 3º quadrimestre, a nota de
  restos a pagar não processados acompanha os indicadores de pessoal.
- **Acessibilidade**: cada UF é um link focável (Tab, Enter) com nome acessível "UF: valor, período";
  hover e foco mostram valor, unidade e período; uma tabela com as 27 UFs acompanha o mapa; a paleta é
  segura para daltonismo e o padrão hachurado distingue "sem dado" sem depender de cor.
- **Malha**: geometrias oficiais do IBGE (`/geographies/states/boundaries`, S2). Sem malha coletada, a
  página avisa e mantém a tabela. A malha segue a RFC 7946 (anel externo anti-horário); o frontend
  reorienta os anéis para a convenção do d3-geo antes de projetar (sem alterar coordenadas), o que é
  testado com a amostra real do IBGE e exercitado no E2E por quadrados sintéticos anti-horários.

## Fora do escopo agora

Resultados de 2018–2022 (só como série própria, nunca emendada); resultados com RPPS ou abaixo da
linha; pessoal dos demais poderes e total do ente (limite de 60%, LRF art. 19); RCL ajustada isolada;
investimentos empenhados ou pagos; DC/RCL, passivo atuarial e metas da LDO; valores per capita, em % do
PIB estadual e rankings (dependem do PIB estadual do IBGE).
