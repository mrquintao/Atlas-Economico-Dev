
# PROJETO: ATLAS ECONÔMICO BRASILEIRO
## Especificação técnica, arquitetura e instruções de implementação

Você atuará como um engenheiro de software sênior, arquiteto de sistemas e especialista em engenharia de dados.

Seu objetivo é me ajudar a projetar e implementar uma plataforma web de visualização, análise e exploração histórica de dados econômicos e fiscais do Brasil.

Não quero apenas um protótipo visual ou uma aplicação com dados fictícios. Quero construir progressivamente um produto funcional, baseado em dados reais, rastreáveis e provenientes de fontes oficiais.

Você deverá tomar decisões técnicas fundamentadas, propor melhorias quando necessário, escrever código organizado e implementar o projeto em etapas verificáveis.

O nome provisório é:

ATLAS ECONÔMICO BRASILEIRO

==================================================
1. CONTEXTO E MOTIVAÇÃO
==================================================

Quero desenvolver um projeto pessoal de tecnologia, economia, análise de dados e transparência pública.

A ideia surge do interesse em compreender, visualizar e apresentar a evolução da economia brasileira ao longo de diferentes períodos históricos e governos.

Diversos indicadores econômicos estão disponíveis em portais oficiais, como Banco Central, IBGE e Tesouro Nacional.

Entretanto, essas informações frequentemente estão dispersas em APIs, planilhas, relatórios e sistemas diferentes.

O objetivo é reunir esses dados em uma plataforma unificada, visualmente intuitiva, tecnicamente confiável e capaz de apresentar a evolução histórica dos indicadores econômicos brasileiros.

Inicialmente, quero analisar a economia nacional.

Posteriormente, quero expandir para todos os 26 estados brasileiros e o Distrito Federal, permitindo explorar as finanças públicas e indicadores regionais de cada unidade federativa.

A aplicação deve ajudar a responder perguntas como:

- Como a dívida pública brasileira evoluiu desde 2008?
- Qual era a taxa Selic em determinado período?
- Como a inflação se comportou durante diferentes governos?
- Como determinados indicadores evoluíram simultaneamente?
- Qual foi a variação da dívida em relação ao PIB?
- Quais estados possuem maior dívida em relação à receita?
- Como receitas, despesas e resultados fiscais evoluíram?
- Quais indicadores econômicos apresentaram mudanças expressivas em determinados períodos?
- Como comparar indicadores entre governos, anos e estados?

A plataforma deve ser apartidária, transparente, baseada em evidências e não atribuir relações de causa e efeito sem fundamentação.

Não é um sistema de apuração eleitoral, previsão eleitoral ou propaganda política.

==================================================
2. VISÃO DO PRODUTO
==================================================

Construir um observatório econômico interativo com três dimensões principais.

A. EVOLUÇÃO HISTÓRICA

Visualizar indicadores econômicos ao longo do tempo.

Exemplos:
- Selic
- IPCA
- Dívida pública
- Dívida/PIB
- PIB
- Receitas governamentais
- Despesas governamentais
- Resultado primário
- Resultado nominal

B. EXPLORAÇÃO GEOGRÁFICA

Visualizar informações por estados brasileiros.

O usuário poderá selecionar uma unidade federativa diretamente no mapa, acessar seus indicadores e comparar suas informações com outras unidades.

C. RELACIONAMENTOS ECONÔMICOS

Investigar relações históricas entre indicadores e acontecimentos.

Exemplos:
- Selic e inflação
- Selic e atividade econômica
- Dívida e PIB
- Receitas e despesas
- Crescimento econômico e situação fiscal

Essas relações deverão ser visualizadas inicialmente por séries temporais e comparações estatísticas.

Em etapas futuras, poderão ser utilizados grafos interativos.

IMPORTANTE:
Correlação não significa causalidade.

==================================================
3. OBJETIVOS PRINCIPAIS
==================================================

O sistema deve:

1. Consumir dados econômicos e fiscais de fontes oficiais.

2. Armazenar séries históricas em banco próprio.

3. Automatizar a atualização dos dados.

4. Exibir indicadores cronologicamente.

5. Permitir selecionar diferentes intervalos temporais.

6. Disponibilizar gráficos interativos.

7. Permitir comparar indicadores econômicos.

8. Identificar claramente a fonte de cada informação.

9. Preparar a arquitetura para dados nacionais e estaduais.

10. Permitir expansão futura para análises avançadas e IA.

11. Priorizar precisão, auditabilidade e clareza.

12. Possuir interface moderna, responsiva e acessível.

==================================================
4. PRINCÍPIOS OBRIGATÓRIOS
==================================================

4.1. Dados reais

Nenhum indicador econômico apresentado como real poderá ser inventado, estimado arbitrariamente ou gerado por inteligência artificial.

O sistema deverá utilizar dados provenientes de fontes oficiais.

Dados sintéticos poderão ser utilizados exclusivamente em testes automatizados ou exemplos explicitamente identificados como demonstrativos.

4.2. Transparência

Toda informação deverá possuir metadados que permitam identificar:

- Fonte oficial
- Identificador da série
- Unidade de medida
- Frequência
- Período de referência
- Data de publicação, quando disponível
- Data da última coleta
- Metodologia
- Link para consulta na fonte

4.3. Integridade histórica

As séries precisam preservar suas definições.

Não devemos misturar diferentes conceitos de dívida pública como se fossem equivalentes.

Também não devemos comparar valores de unidades diferentes sem realizar as transformações matemáticas necessárias.

4.4. Neutralidade política

A plataforma deverá mostrar indicadores objetivos.

Comparações entre governos poderão ser implementadas futuramente, mas não devem sugerir automaticamente que determinado presidente ou governador causou uma variação econômica.

4.5. Evolução incremental

Não tente implementar todas as funcionalidades ao mesmo tempo.

A primeira entrega deve ser pequena, funcional, testável e baseada em dados reais.

==================================================
5. ESCOPO DA PRIMEIRA VERSÃO (MVP)
==================================================

A primeira versão deverá focar exclusivamente no Brasil como unidade nacional.

Título da primeira interface:

BRASIL EM PERSPECTIVA

Indicadores obrigatórios:

1. Meta da taxa Selic
2. Inflação medida pelo IPCA acumulado em 12 meses
3. Dívida Bruta do Governo Geral em percentual do PIB

Período histórico inicial:

Janeiro de 2008 até a última observação oficial disponível de cada indicador.

O intervalo deve ser configurável, permitindo expansão para períodos anteriores quando os dados e as metodologias forem compatíveis.

FUNCIONALIDADES DO MVP:

- Dashboard nacional
- Três gráficos econômicos interativos
- Seleção do intervalo histórico
- Exibição das datas
- Tooltips informativos
- Zoom e navegação nos gráficos
- Comparação visual entre indicadores
- Indicadores de valor mais recente
- Variação entre períodos
- Descrição dos indicadores
- Fonte oficial vinculada
- Data da última atualização dos dados
- Estados de carregamento
- Tratamento de erros
- Interface responsiva
- Suporte a desktop e dispositivos móveis

Os gráficos deverão ser sincronizados temporalmente.

Exemplo:

Se o usuário selecionar o período de 2015 a 2022, os três gráficos deverão exibir esse mesmo intervalo.

A frequência original das séries deverá ser preservada.

Para visualização mensal da Selic, utilizar o último valor oficialmente disponível em cada mês, identificando claramente essa regra de agregação.

Não utilizar médias arbitrárias nem interpolação silenciosa.

Não alterar a definição original dos indicadores.

==================================================
6. FONTES OFICIAIS DE DADOS
==================================================

Utilizar preferencialmente APIs públicas e documentadas.

6.1. BANCO CENTRAL DO BRASIL

Portal:
https://dadosabertos.bcb.gov.br/

API de séries temporais:
https://api.bcb.gov.br/

Séries inicialmente selecionadas:

SGS 432:
Meta da taxa Selic definida pelo Copom.

Características:
- Frequência diária
- Unidade percentual ao ano
- Aplicação nacional

Referência:
https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom

SGS 13762:
Dívida Bruta do Governo Geral em percentual do PIB, metodologia utilizada a partir de 2008.

Características:
- Frequência mensal
- Unidade percentual do PIB
- Aplicação nacional

Referência:
https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008

O conector deverá seguir a documentação atual do serviço BCData/SGS.

IMPORTANTE:
Séries diárias do SGS possuem limitações de consulta por intervalo.

Implementar paginação temporal ou coleta em janelas compatíveis com os limites oficiais, incluindo a restrição de até 10 anos por consulta aplicável às séries diárias.

6.2. IBGE

Portal:
https://www.ibge.gov.br/

Documentação das APIs:
https://servicodados.ibge.gov.br/api/docs/

SIDRA:
https://sidra.ibge.gov.br/

API SIDRA:
https://apisidra.ibge.gov.br/

Indicador inicial:
IPCA acumulado em 12 meses.

Investigar a tabela 1737 do SIDRA, identificar a variável correta e confirmar a metodologia antes de implementar.

Não confundir:
- Variação mensal do IPCA
- Acumulado no ano
- Acumulado em 12 meses
- Número-índice

Usar o acumulado em 12 meses no dashboard inicial.

Na expansão estadual, lembrar que a divulgação regional do IPCA ocorre por áreas pesquisadas, não necessariamente por todas as 27 unidades federativas.

Não apresentar índices regionais como indicadores oficiais estaduais sem correspondência metodológica.

6.3. TESOURO NACIONAL

Portal:
https://www.tesourotransparente.gov.br/

APIs:
https://www.gov.br/tesouronacional/pt-br/central-de-conteudo/apis

Fontes para expansão:

- Resultado do Tesouro Nacional
- Estoque da Dívida Pública Federal
- Séries fiscais
- Receitas e despesas
- Resultado primário
- Resultado nominal

O Tesouro não precisa ser integrado integralmente no primeiro MVP.

Entretanto, sua integração futura deverá ser considerada na arquitetura.

6.4. SICONFI

Documentação:
https://apidatalake.tesouro.gov.br/docs/siconfi/

Fonte principal para expansão estadual.

Investigar:
- Relatório Resumido da Execução Orçamentária (RREO)
- Relatório de Gestão Fiscal (RGF)
- Declaração de Contas Anuais (DCA)
- Matriz de Saldos Contábeis (MSC)

A API pública do SICONFI documenta limite de uma requisição por segundo.

Implementar controle de taxa, paginação, tentativas com backoff e coleta incremental.

6.5. MALHAS GEOGRÁFICAS DO IBGE

Utilizar as geometrias oficiais dos estados brasileiros.

Investigar:
https://servicodados.ibge.gov.br/api/v3/malhas

Preferir GeoJSON ou formato compatível.

Usar os códigos oficiais do IBGE como identificadores geográficos canônicos.

Validar a correspondência entre códigos IBGE, siglas das unidades federativas e identificadores das fontes fiscais.

==================================================
7. STACK TECNOLÓGICA
==================================================

Priorizar uma stack moderna, madura, de código aberto e adequada para evolução de longo prazo.

FRONTEND:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Apache ECharts
- D3 Geo

RESPONSABILIDADES:

Next.js:
Interface, navegação e páginas.

TypeScript:
Tipagem e segurança estrutural.

Tailwind:
Estilização.

shadcn/ui:
Componentes reutilizáveis e acessíveis.

ECharts:
Séries temporais, tooltips, zoom e comparações.

D3 Geo:
Renderização geográfica e interação com estados.

BACKEND:

- Python 3.12 ou versão estável compatível
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- httpx
- Pandas apenas quando realmente necessário

RESPONSABILIDADES:

- Integração com fontes externas
- Normalização de indicadores
- Regras de negócio
- Consulta de séries históricas
- Cálculos derivados
- Metadados
- API REST

BANCO DE DADOS:

PostgreSQL.

Não utilizar Neo4j na primeira versão.

A necessidade de banco de grafos será reavaliada em etapas posteriores.

INFRAESTRUTURA:

- Docker
- Docker Compose
- Git
- GitHub Actions
- Variáveis de ambiente
- Logs estruturados

AUTOMAÇÃO:

Inicialmente, utilizar scripts Python e agendamentos simples.

Não adicionar infraestrutura complexa de filas e processamento distribuído antes que exista necessidade real.

TESTES:

Backend:
pytest.

Frontend:
Vitest e Testing Library.

Testes end-to-end:
Playwright, quando o fluxo principal estiver implementado.

==================================================
8. ARQUITETURA DO SISTEMA
==================================================

Fluxo principal:

FONTES OFICIAIS
      |
      v
CONECTORES PYTHON
      |
      v
VALIDAÇÃO DOS DADOS
      |
      v
NORMALIZAÇÃO
      |
      v
POSTGRESQL
      |
      v
FASTAPI
      |
      v
NEXT.JS
      |
      v
DASHBOARD INTERATIVO

O frontend não deverá depender diretamente das APIs externas.

A coleta deverá ocorrer por meio do backend.

O backend deverá armazenar os dados e oferecer uma interface consistente para o frontend.

Esse desenho busca:

- Evitar dependência direta de APIs instáveis
- Melhorar desempenho
- Permitir cache
- Facilitar validação
- Controlar limites de acesso
- Manter histórico
- Unificar formatos de dados
- Facilitar testes

A arquitetura deverá seguir princípios de separação de responsabilidades, sem exagerar na abstração.

Não implementar microserviços no MVP.

Utilizar inicialmente um monorepositório simples.

==================================================
9. ORGANIZAÇÃO SUGERIDA DO REPOSITÓRIO
==================================================

atlas-economico/
|
|-- apps/
|   |-- web/
|       |-- src/
|           |-- app/
|           |-- components/
|           |-- features/
|           |-- hooks/
|           |-- lib/
|           |-- types/
|
|-- services/
|   |-- api/
|       |-- app/
|           |-- api/
|           |-- core/
|           |-- db/
|           |-- models/
|           |-- schemas/
|           |-- services/
|           |-- integrations/
|           |-- ingestion/
|           |-- repositories/
|       |-- migrations/
|       |-- tests/
|
|-- packages/
|   |-- shared/
|
|-- infra/
|   |-- docker/
|
|-- docs/
|
|-- scripts/
|
|-- docker-compose.yml
|-- .env.example
|-- README.md

Esta estrutura é uma sugestão.

Você poderá ajustá-la para reduzir complexidade desnecessária.

Evite criar diretórios vazios e abstrações sem aplicação concreta.

==================================================
10. MODELAGEM DO BANCO DE DADOS
==================================================

A modelagem deverá permitir adicionar indicadores sem criar uma nova tabela para cada um.

ENTIDADE: data_sources

Representa as fontes oficiais.

Campos sugeridos:

- id
- name
- acronym
- organization
- base_url
- documentation_url
- created_at
- updated_at

ENTIDADE: indicators

Catálogo dos indicadores.

Campos:

- id
- code
- name
- description
- source_id
- source_series_code
- unit
- frequency
- geographic_level
- methodology
- methodology_version
- first_available_date
- created_at
- updated_at

Exemplos de códigos internos:

SELIC_TARGET
IPCA_12M
DBGG_GDP

ENTIDADE: geographic_units

Representa as unidades geográficas.

Campos:

- id
- ibge_code
- acronym
- name
- geographic_level
- parent_id

Exemplos:

Brasil
Minas Gerais
São Paulo
Rio de Janeiro
Distrito Federal

Usar identificadores geográficos oficiais.

ENTIDADE: observations

Armazena os valores observados.

Campos:

- id
- indicator_id
- geographic_unit_id
- reference_date
- period_start
- period_end
- value
- published_at
- collected_at
- source_reference
- metadata_json
- created_at
- updated_at

Utilizar tipos numéricos apropriados, preferencialmente NUMERIC/DECIMAL, para armazenamento de dados econômicos.

Criar índices para consultas por:

- Indicador
- Unidade geográfica
- Data

Implementar restrições de unicidade adequadas para evitar observações duplicadas.

ENTIDADE: ingestion_runs

Histórico de execução dos conectores.

Campos:

- id
- source_id
- started_at
- finished_at
- status
- records_received
- records_inserted
- records_updated
- error_message
- metadata_json

ENTIDADE: observation_revisions (opcional no MVP)

Histórico de revisões de dados publicados.

Campos:

- id
- observation_id
- previous_value
- new_value
- detected_at
- ingestion_run_id

IMPORTANTE:

Projetar o sistema para registrar revisões históricas.

O armazenamento deve permitir identificar quando uma fonte oficial altera um valor anteriormente publicado.

Registrar também, quando viável, uma cópia ou hash do payload bruto recebido.

A ingestão precisa ser idempotente: executá-la várias vezes com os mesmos dados não pode criar duplicações.

==================================================
11. PIPELINE DE INGESTÃO DE DADOS
==================================================

Cada fonte deve possuir um conector independente.

Por exemplo:

BCBConnector
IBGEConnector
TesouroConnector
SiconfiConnector

No MVP, implementar apenas os conectores necessários.

O pipeline deverá executar:

1. Requisitar dados oficiais.
2. Tratar falhas HTTP.
3. Respeitar limites da API.
4. Validar estrutura da resposta.
5. Converter datas e números.
6. Normalizar unidades.
7. Identificar registros duplicados.
8. Comparar com observações armazenadas.
9. Inserir ou atualizar dados.
10. Registrar execução e erros.
11. Disponibilizar os dados para consulta.

Requisitos:

- Timeouts explícitos
- Retry com exponential backoff
- Rate limiting
- Logging estruturado
- Validação de payload
- Coleta incremental
- Tratamento de respostas vazias
- Tratamento de valores nulos
- Preservação dos dados anteriores em caso de falha
- Suporte a reprocessamento histórico

Os conectores não devem assumir que os formatos das APIs permanecerão imutáveis.

Sempre documentar endpoints e parâmetros efetivamente utilizados.

==================================================
12. API INTERNA
==================================================

Implementar uma API REST simples e documentada automaticamente pelo FastAPI.

Endpoints sugeridos:

GET /api/v1/health

Retorna o estado da aplicação.

GET /api/v1/indicators

Lista indicadores disponíveis.

GET /api/v1/indicators/{code}

Retorna metadados de um indicador.

GET /api/v1/indicators/{code}/observations

Parâmetros:

- start_date
- end_date
- geography
- frequency

Retorna observações históricas.

GET /api/v1/dashboard/national

Retorna dados resumidos do dashboard nacional.

GET /api/v1/sources

Lista fontes oficiais.

GET /api/v1/geographies

Lista unidades geográficas cadastradas.

FUTURAMENTE:

GET /api/v1/states/{uf}/dashboard

GET /api/v1/states/{uf}/indicators

GET /api/v1/compare

GET /api/v1/events

GET /api/v1/relationships

Requisitos da API:

- Esquemas Pydantic
- Paginação quando aplicável
- Validação de parâmetros
- Formato JSON consistente
- Tratamento de erros
- Documentação OpenAPI
- Datas em formato ISO 8601
- Valores e unidades explicitamente identificados
- Consultas otimizadas

Não retornar uma série nacional como se fosse um indicador estadual.

==================================================
13. INTERFACE E EXPERIÊNCIA DO USUÁRIO
==================================================

Quero uma interface semelhante a plataformas modernas de análise de dados, com aparência profissional e limpa.

Referências conceituais:

- Observatórios de dados econômicos
- Dashboards analíticos
- Ferramentas de exploração de séries temporais
- Plataformas de transparência pública

Estilo visual:

- Minimalista
- Profissional
- Boa hierarquia visual
- Excelente legibilidade
- Responsivo
- Suporte a tema claro e escuro
- Animações discretas
- Sem excesso de elementos decorativos

A interface deverá priorizar a compreensão das informações.

ESTRUTURA INICIAL:

Cabeçalho:

ATLAS ECONÔMICO BRASILEIRO

Navegação futura:

- Visão Geral
- Brasil
- Estados
- Comparações
- Metodologia
- Fontes de Dados

No MVP, implementar somente as páginas funcionais.

DASHBOARD NACIONAL:

A. Título

Brasil em Perspectiva

B. Introdução

Breve texto explicativo sobre a plataforma.

C. Indicadores destacados

Cards com os valores mais recentes:

- Selic
- IPCA 12 meses
- Dívida bruta/PIB

Cada card deve mostrar:

- Nome
- Valor
- Unidade
- Período de referência
- Fonte

D. Filtros

Selecionar:

- Data inicial
- Data final
- Período predefinido

Exemplos:

5 anos
10 anos
Todo o histórico disponível

E. Gráficos

Três gráficos de série temporal.

Selic
Inflação
Dívida/PIB

Todos conectados ao mesmo intervalo de datas.

F. Informações metodológicas

Cada gráfico deverá oferecer:

- Descrição do indicador
- Unidade utilizada
- Fonte
- Metodologia
- Link oficial
- Data de atualização

G. Estados vazios

Quando não houver dados, mostrar uma mensagem clara.

Não substituir automaticamente dados ausentes por zero.

==================================================
14. REQUISITOS DOS GRÁFICOS
==================================================

Utilizar Apache ECharts.

Funcionalidades:

- Linha temporal
- Tooltip
- Zoom
- Seleção de período
- Formatação em português brasileiro
- Valores percentuais
- Identificação da unidade
- Destaque do período selecionado
- Interação acessível
- Boa experiência mobile

Evitar gráficos enganosos.

Indicadores com escalas diferentes devem aparecer, por padrão, em gráficos separados.

Não usar dois eixos verticais de forma indiscriminada.

Ao comparar indicadores, identificar claramente as escalas e unidades.

Para indicadores de taxa, distinguir:

- Variação percentual
- Pontos percentuais
- Percentual do PIB

Exemplo:

Selic de 10% para 12% representa aumento de 2 pontos percentuais, não simplesmente 2%.

Implementar funções de formatação reutilizáveis.

==================================================
15. PREPARAÇÃO PARA O MAPA DO BRASIL
==================================================

Embora o mapa não precise integrar o primeiro MVP, a arquitetura deve estar pronta para suportá-lo.

Na segunda fase, implementar um mapa interativo do Brasil.

Características:

- 26 estados e Distrito Federal
- Geometrias oficiais
- Estados clicáveis
- Hover com informações
- Seleção visual
- Mapa de calor por indicador
- Legenda
- Escala de cores acessível
- Responsividade
- Integração com filtros temporais

Ao clicar em Minas Gerais, por exemplo, o usuário deverá navegar para:

/estados/MG

Essa página apresentará indicadores fiscais e econômicos efetivamente disponíveis para Minas Gerais.

O mapa deverá respeitar valores ausentes.

Estados sem informação não poderão ser apresentados como se possuíssem valor zero.

==================================================
16. EXPANSÃO PARA CONTAS ESTADUAIS
==================================================

Na segunda fase, integrar fontes oficiais do Tesouro e SICONFI.

Indicadores potenciais:

- Receita corrente líquida
- Receita total
- Despesa total
- Despesa com pessoal
- Dívida consolidada
- Dívida consolidada líquida
- Relação dívida/receita corrente líquida
- Resultado primário
- Resultado nominal
- Investimentos
- PIB estadual

Cada indicador deverá ter sua definição fiscal e fonte devidamente registradas.

Diferenciar:

- Receitas realizadas e previstas
- Despesas empenhadas, liquidadas e pagas
- Valores anuais e acumulados
- Estoques e fluxos
- Dívida bruta e dívida líquida

Não misturar métricas sem fundamentação contábil.

Criar uma página individual para cada estado.

Exemplo:

/estados/MG
/estados/SP
/estados/RJ

Funcionalidades futuras:

- Comparação entre estados
- Ranking por indicador
- Ranking com escolha do período
- Evolução histórica
- Seleção de múltiplos estados
- Comparação por valores absolutos
- Comparação por indicadores proporcionais

Evitar rankings que desconsiderem o tamanho econômico dos estados.

Sempre que adequado, oferecer comparações relativas, como dívida/receita ou despesa/PIB.

==================================================
17. EXPLORADOR DE RELACIONAMENTOS
==================================================

Funcionalidade planejada para fase futura.

O usuário poderá investigar relações entre indicadores econômicos.

Exemplo:

SELIC
  |
  |-- Inflação
  |
  |-- Crédito
  |
  |-- Atividade econômica
  |
  |-- Serviço da dívida

Utilizar inicialmente bibliotecas de visualização de grafos, como Cytoscape.js ou D3, se necessário.

Não introduzir Neo4j automaticamente.

Primeiro avaliar se o PostgreSQL suporta adequadamente o modelo de relacionamentos.

O sistema poderá permitir:

- Seleção de nós
- Expansão de relações
- Abertura dos gráficos relacionados
- Comparações temporais
- Exploração de correlações
- Comparação com defasagens temporais

Os vínculos deverão indicar se representam:

- Uma relação conceitual
- Uma hipótese econômica
- Uma relação estatística observada
- Uma relação causal sustentada por estudo específico

Nunca tratar automaticamente correlação como causalidade.

==================================================
18. LINHA DO TEMPO HISTÓRICA
==================================================

Implementar posteriormente uma linha do tempo de acontecimentos econômicos brasileiros.

Exemplos de categorias:

- Mudanças de governo
- Crises econômicas
- Alterações de política monetária
- Reformas fiscais
- Mudanças metodológicas
- Eventos econômicos internacionais

Essa funcionalidade deverá permitir identificar acontecimentos relevantes sobre os gráficos.

Estrutura futura de eventos:

- id
- title
- description
- start_date
- end_date
- category
- source_url
- created_at

Todo evento deverá possuir fonte verificável.

Não apresentar automaticamente um evento como causa de determinado movimento econômico.

==================================================
19. FUTURA INTEGRAÇÃO COM INTELIGÊNCIA ARTIFICIAL
==================================================

A IA poderá ser incorporada posteriormente.

Objetivo:

Permitir que usuários façam perguntas em linguagem natural.

Exemplos:

"Como evoluiu a dívida pública entre 2015 e 2025?"

"Compare a Selic e o IPCA no período selecionado."

"Mostre os indicadores fiscais de Minas Gerais."

"Qual foi a variação da dívida/PIB em determinado intervalo?"

A IA deverá atuar como interface de consulta e explicação.

Regras obrigatórias:

- Não inventar valores.
- Consultar dados armazenados e validados.
- Executar cálculos por funções determinísticas.
- Apresentar fontes.
- Informar períodos utilizados.
- Identificar ausência de dados.
- Separar observação estatística de interpretação.

Não implementar integração com LLM no primeiro MVP.

==================================================
20. PADRÕES DE QUALIDADE
==================================================

CÓDIGO:

- Tipagem explícita
- Componentes reutilizáveis
- Funções com responsabilidades claras
- Separação entre apresentação e regras de negócio
- Evitar duplicação
- Tratamento de erros
- Testes para regras críticas
- Convenções consistentes
- Documentação objetiva

SEGURANÇA:

- Credenciais apenas por variáveis de ambiente
- Nenhum segredo no Git
- Validação de entradas
- CORS configurado
- Dependências atualizadas
- Consultas parametrizadas ao banco

PERFORMANCE:

- Consultas otimizadas
- Índices apropriados
- Cache quando necessário
- Redução de chamadas externas
- Carregamento eficiente dos gráficos
- Evitar downloads completos a cada acesso

ACESSIBILIDADE:

- Contraste adequado
- Navegação por teclado
- Rótulos acessíveis
- Legendas compreensíveis
- Layout responsivo
- Informações importantes não dependentes apenas de cores

==================================================
21. TESTES E VALIDAÇÃO
==================================================

Criar testes para:

1. Parsing de respostas oficiais.
2. Conversão de datas.
3. Conversão de números.
4. Validação de indicadores.
5. Detecção de duplicidades.
6. Ingestão idempotente.
7. Tratamento de valores ausentes.
8. Filtragem por intervalo temporal.
9. Consultas ao banco.
10. Respostas da API.
11. Tratamento de indisponibilidade externa.
12. Sincronização de filtros dos gráficos.

Utilizar fixtures locais nos testes.

Fixtures sintéticas deverão ser usadas somente no ambiente de testes.

Para validar a integração real, executar ao menos uma coleta verificável e confrontar amostras de dados com a fonte oficial.

Não declarar integração concluída sem uma verificação efetiva.

==================================================
22. DOCUMENTAÇÃO
==================================================

Criar README.md contendo:

- Visão do projeto
- Objetivos
- Stack utilizada
- Estrutura de diretórios
- Pré-requisitos
- Instalação
- Configuração de ambiente
- Inicialização do banco
- Execução das migrações
- Coleta inicial de dados
- Inicialização do backend
- Inicialização do frontend
- Execução dos testes
- Links das fontes de dados

Também criar documentação para:

- Catálogo de indicadores
- Metodologias
- Arquitetura
- Endpoints
- Pipeline de ingestão
- Decisões técnicas importantes

==================================================
23. ROADMAP
==================================================

FASE 1 — MVP NACIONAL

Objetivo:
Entregar uma aplicação funcional com dados econômicos nacionais reais.

Entregas:

1. Estrutura do projeto
2. Docker Compose
3. PostgreSQL
4. Backend FastAPI
5. Modelagem inicial
6. Migrações
7. Conector Bacen
8. Conector IBGE
9. Pipeline de ingestão
10. API interna
11. Frontend Next.js
12. Dashboard nacional
13. Gráficos sincronizados
14. Metadados e fontes
15. Testes
16. Documentação

FASE 2 — ATLAS ESTADUAL

Objetivo:
Incluir os estados brasileiros.

Entregas:

1. Integração com SICONFI
2. Catálogo de indicadores estaduais
3. Modelagem e normalização fiscal
4. Integração com geometrias IBGE
5. Mapa interativo
6. Página por estado
7. Comparação entre estados
8. Rankings e visualização temporal

FASE 3 — ANÁLISE AVANÇADA

Objetivo:
Transformar o dashboard em uma plataforma de investigação econômica.

Entregas:

1. Linha do tempo de eventos
2. Comparações entre governos
3. Comparações econômicas avançadas
4. Valores corrigidos pela inflação
5. Exploração de relacionamentos
6. Grafos interativos
7. Correlações estatísticas
8. Relatórios exportáveis
9. IA para consultas em linguagem natural

==================================================
24. O QUE NÃO DEVE SER IMPLEMENTADO AGORA
==================================================

Evitar no MVP:

- Neo4j
- Microserviços
- Kubernetes
- Filas distribuídas
- Sistemas complexos de autenticação
- Contas de usuários
- Inteligência artificial
- Modelos preditivos
- Análises eleitorais
- Grafos econômicos completos
- Coleta de dados de todos os municípios
- Mapas estaduais com dados fictícios
- Infraestrutura desnecessariamente complexa

Nosso objetivo é produzir software funcional, não complexidade técnica.

==================================================
25. CRITÉRIOS DE ACEITE DO MVP
==================================================

O MVP será considerado funcional quando:

[ ] O projeto puder ser iniciado localmente com instruções claras.

[ ] O PostgreSQL estiver operacional.

[ ] As migrações forem executadas corretamente.

[ ] O backend disponibilizar a documentação OpenAPI.

[ ] O conector Bacen coletar dados reais da Selic.

[ ] O conector Bacen coletar dados reais da dívida bruta/PIB.

[ ] O conector IBGE coletar dados reais do IPCA acumulado em 12 meses.

[ ] As observações forem armazenadas corretamente.

[ ] A repetição da coleta não gerar duplicações.

[ ] A API retornar séries filtradas por data.

[ ] O frontend consumir a API interna.

[ ] Os três gráficos exibirem dados reais.

[ ] O filtro temporal funcionar para todos os gráficos.

[ ] A interface apresentar fonte, unidade e data dos indicadores.

[ ] A aplicação tratar dados ausentes sem inventar valores.

[ ] Os testes principais forem executados.

[ ] O README explicar como executar toda a aplicação.

[ ] A estrutura permitir adicionar indicadores estaduais futuramente.

==================================================
26. COMO VOCÊ DEVE TRABALHAR
==================================================

Quero que você atue como responsável pela implementação técnica, não apenas como consultor.

Siga estes princípios:

1. Analise a especificação e identifique riscos técnicos relevantes.

2. Verifique a estrutura do repositório existente antes de criar arquivos.

3. Se o repositório estiver vazio, inicialize o projeto.

4. Respeite o escopo do MVP.

5. Prefira decisões simples, robustas e justificáveis.

6. Implemente código real e executável.

7. Não produza apenas pseudocódigo.

8. Não crie implementações fictícias que simulem integração real.

9. Verifique as documentações oficiais antes de fixar endpoints.

10. Mantenha o projeto executável a cada etapa.

11. Escreva testes para funcionalidades importantes.

12. Execute build, lint e testes quando o ambiente permitir.

13. Registre problemas encontrados.

14. Não afirme que algo funciona sem ter validado.

15. Explique resumidamente decisões arquiteturais relevantes.

16. Não altere todo o escopo sem necessidade.

17. Evite solicitar confirmações sobre decisões técnicas comuns. Escolha uma alternativa razoável e documente.

18. Não avance prematuramente para funcionalidades da fase 2 ou 3.

19. Priorize código limpo, rastreabilidade dos dados e experiência do usuário.

20. Se algum serviço externo estiver indisponível, implemente o conector, seus testes e documente claramente a validação pendente. Não substitua dados reais por números inventados.

==================================================
27. PRIMEIRA TAREFA DE IMPLEMENTAÇÃO
==================================================

Comece pela fundação do MVP nacional.

Ordem sugerida:

PASSO 1

Analisar o repositório e definir a estrutura inicial do monorepositório.

PASSO 2

Configurar o ambiente de desenvolvimento:

- Next.js
- FastAPI
- PostgreSQL
- Docker Compose
- Variáveis de ambiente
- Ferramentas de teste

PASSO 3

Implementar o modelo de banco de dados:

- data_sources
- indicators
- geographic_units
- observations
- ingestion_runs

PASSO 4

Configurar SQLAlchemy e Alembic.

PASSO 5

Criar os registros iniciais dos indicadores:

- SELIC_TARGET
- DBGG_GDP
- IPCA_12M

PASSO 6

Implementar o primeiro conector real:

Banco Central, SGS 432.

O conector deverá:

- Consultar dados oficiais
- Respeitar limites temporais da API
- Validar resposta
- Converter datas
- Converter valores
- Persistir observações
- Registrar execução
- Evitar duplicações

PASSO 7

Criar endpoint para consulta:

GET /api/v1/indicators/SELIC_TARGET/observations

PASSO 8

Criar uma página inicial que consuma esse endpoint e renderize um gráfico interativo da Selic.

PASSO 9

Criar testes e documentação de execução.

Essa deverá ser a primeira entrega vertical completa:

API oficial -> Coleta -> Banco -> API interna -> Frontend -> Gráfico.

Depois disso, evoluir incrementalmente para a dívida/PIB e o IPCA.

==================================================
28. ENTREGÁVEIS DA PRIMEIRA ITERAÇÃO
==================================================

Espero receber:

1. Estrutura funcional do repositório.

2. Configuração do ambiente local.

3. Banco e migrações.

4. Conector real da Selic.

5. API para consulta histórica.

6. Página web com gráfico conectado à API.

7. Tratamento básico de erros.

8. Testes essenciais.

9. README com comandos exatos para execução.

10. Resumo do que foi implementado, do que foi efetivamente testado e do que permanece pendente.

Se o trabalho precisar ser dividido em várias interações, utilize marcos verificáveis, mantendo o projeto consistente a cada etapa.

==================================================
29. VISÃO DE LONGO PRAZO
==================================================

O Atlas Econômico Brasileiro deverá evoluir para uma plataforma pública de exploração da economia e das finanças governamentais brasileiras.

Sua principal vantagem não será apenas exibir gráficos.

Será oferecer:

- Dados confiáveis
- Histórico consistente
- Transparência metodológica
- Comparações econômicas
- Exploração geográfica
- Rastreabilidade
- Interface acessível
- Possibilidade de análises aprofundadas

A ideia é construir uma ferramenta que permita que qualquer pessoa explore dados econômicos brasileiros sem depender exclusivamente de interpretações prontas.

O produto deverá ser tecnicamente sólido, visualmente atraente e aberto à evolução.

==================================================
30. INSTRUÇÃO FINAL
==================================================

Agora inicie efetivamente o desenvolvimento.

Primeiro, faça uma avaliação breve da arquitetura proposta e aponte apenas eventuais problemas críticos que precisam ser corrigidos antes da implementação.

Em seguida, execute a PRIMEIRA TAREFA DE IMPLEMENTAÇÃO descrita na seção 27.

Não fique apenas no planejamento.

Crie os arquivos, configurações, modelos, conectores, endpoints, componentes e testes necessários, de acordo com as ferramentas e permissões disponíveis no ambiente.

Trabalhe como um engenheiro responsável pela entrega de um produto real.

O objetivo imediato é conseguir executar localmente uma aplicação que mostre a evolução histórica da Selic, alimentada por dados oficiais do Banco Central e persistidos em PostgreSQL.

A partir dessa base, evoluiremos para o restante do Atlas Econômico Brasileiro.
