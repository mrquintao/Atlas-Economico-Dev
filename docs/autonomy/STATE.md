# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 1 — MVP nacional |
| Entrega ativa | M1 — Robustez (parâmetros desconhecidos, filtros mensais, estados de carregamento) |
| Issue ativa | [#3](https://github.com/mrquintao/Atlas-Economico-Dev/issues/3) |
| PR associado | (a abrir) |
| Branch | `claude/compassionate-mayer-eon3qz` (a partir de `main@c0f3b5c`) |
| Último commit integrado na `main` | `c0f3b5c` — merge do PR #2 (DBGG/PIB e gráficos sincronizados) |
| Próxima entrega elegível após a ativa | M2 — IPCA 12 meses ([#4](https://github.com/mrquintao/Atlas-Economico-Dev/issues/4)) |
| Última validação | PR #2: CI verde (API, Web, Docker); 93 pytest e 41 vitest |

## Bloqueios

| Item | Motivo | Ação necessária | Desde |
|---|---|---|---|
| I1 — proteção da `main` e auto-merge nativo ([#10](https://github.com/mrquintao/Atlas-Economico-Dev/issues/10)) | As ferramentas do agente não configuram regras de branch nem as opções do repositório | Mantenedor: seguir os passos da issue #10. Até lá, o agente aplica o gate da AGENT_POLICY §3 e faz o merge com `merge_pull_request` | 2026-10-21 |
| GitHub Projects (quadro "Atlas Econômico — Autonomous Development") | Sem ferramenta de Projects disponível para o agente | Opcional: o mantenedor cria o quadro; o backlog funciona por labels e milestones nas issues | 2026-10-21 |
| Cores e descrições das labels | Labels criadas automaticamente pelas issues (cinza, sem descrição); não há ferramenta para editá-las | Opcional e cosmético | 2026-10-21 |

## Decisões permanentes de escopo

- **Sem funcionalidades baseadas em LLM no produto** ([ADR 0004](../adr/0004-exclusao-de-funcionalidades-com-llm.md), 2026-10-21).
  A antiga A7 (#26) foi cancelada; a `v1.0.0` (#27) depende de A1–A6.

## Próxima ação recomendada

Concluir a M1 (#3): implementar, validar, auditar com o `qa-auditor`, abrir o PR, integrar quando o gate
for satisfeito e iniciar a M2 (#4), começando pela validação metodológica do SIDRA 1737 pelo `economist`.

## Ambiente de desenvolvimento (lembrete para sessões em nuvem)

- PostgreSQL 16 local: `/usr/lib/postgresql/16/bin`; bancos `atlas` (dados reais, **não destruir**),
  `atlas_test` e `atlas_ci` (descartáveis).
- Sem Docker local: os Dockerfiles são validados pelo job `Docker Compose` do CI.
- Proxy de saída: a API do BCB responde; o SIDRA deve ser testado no início da M2.
