# ADR 0004 — Exclusão permanente de funcionalidades baseadas em LLM

**Status:** aceito (2026-10-21). Decisão do mantenedor, permanente e com prioridade sobre qualquer
instrução anterior em conflito (inclusive o `PROJECT_SPEC.md` original, o roadmap e os prompts de autonomia).

## Contexto

O `PROJECT_SPEC.md` previa, na Fase 3 (§19 e §23 item 9), uma interface de consultas em linguagem
natural apoiada por IA. O roadmap a registrava como entrega A7 (issue #26), já bloqueada por depender de
serviço pago.

## Decisão

O Atlas Econômico Brasileiro **não** implementará funcionalidades que dependam de LLMs:

- assistente de consultas em linguagem natural;
- chatbots e assistentes conversacionais;
- integrações com APIs de LLMs (OpenAI, Anthropic, Gemini etc.);
- RAG, embeddings e bancos vetoriais para funcionalidades de IA generativa;
- geração de análises econômicas ou relatórios por modelos de linguagem;
- qualquer outra funcionalidade do produto cuja execução dependa de um LLM.

Todas as funcionalidades econômicas e estatísticas continuam previstas e usam **algoritmos convencionais,
cálculos verificáveis e dados oficiais**: indicadores e séries históricas, dashboards nacionais e
estaduais, mapas, comparações entre estados e governos, correlações e defasagens, correção monetária,
grafos de relacionamentos (com vínculos declarados ou calculados, nunca gerados por modelo), relatórios e
exportações (montados a partir de dados e textos metodológicos fixos).

A restrição vale para a arquitetura e as funcionalidades **do produto**. O uso do Claude Code e dos
agentes especializados para desenvolver o projeto continua autorizado.

## Consequências

- A entrega A7 foi removida do roadmap e a issue #26 foi fechada como *not planned*, sem substituição
  automática por outra funcionalidade.
- A release `v1.0.0` (A8, issue #27) passa a depender de A1–A6.
- Nenhuma dependência de SDK de LLM, embeddings ou banco vetorial pode ser adicionada a
  `services/api` ou `apps/web`; a auditoria do `qa-auditor` verifica isso.
- Textos explicativos exibidos no produto são escritos e revisados por pessoas ou agentes durante o
  desenvolvimento e versionados no repositório; nunca gerados em tempo de execução.
