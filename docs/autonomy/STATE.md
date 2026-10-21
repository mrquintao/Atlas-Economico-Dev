# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 1 — MVP nacional |
| Última entrega | M1 — Robustez (issue #3), PR #28: parâmetros desconhecidos e repetidos (422), filtro pelo fim do período de referência + índice, presets alinhados ao mês, estados de carregamento consistentes |
| Próxima entrega elegível | **M2 — IPCA 12 meses ([#4](https://github.com/mrquintao/Atlas-Economico-Dev/issues/4))** |
| Issue ativa | nenhuma até o início da M2 |
| Branch | novo branch a partir da `main` atualizada após o merge do PR #28 |
| Último commit integrado na `main` | merge do PR #28 (conferir com `git log origin/main -1`) |
| Última validação | `scripts/check.sh` num clone limpo: 113 pytest (PostgreSQL) e 46 vitest; lint, format, `alembic check`, typecheck e build; navegador com dados reais (cursor 118/118, console limpo); qa-auditor: pronto para PR |

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

Iniciar a M2 (#4): (1) testar o acesso ao SIDRA (`apisidra.ibge.gov.br`) pelo proxy; (2) `economist` valida a
tabela 1737, a variável do acumulado em 12 meses e as amostras; (3) conector `integrations/ibge/sidra.py`
e despacho da ingestão por fonte; (4) seed `IPCA_12M` com `period_*` = mês de referência e janela de 12
meses como metadado (comentário na #4); (5) cartão e terceiro gráfico sincronizado.

## Ambiente de desenvolvimento (lembrete para sessões em nuvem)

- PostgreSQL 16 local: `/usr/lib/postgresql/16/bin`, dados em `/tmp/pgdata` (sobrevive a reinícios;
  após um reboot: `su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pgdata/log -o '-p 5432 -k /tmp' start"`).
  Bancos: `atlas` (dados reais, **não destruir**; migrado até 0004), `atlas_test` e `atlas_ci` (descartáveis).
- Validação local: `TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh`.
- Sem Docker local: os Dockerfiles são validados pelo job `Docker Compose` do CI.
- Proxy de saída: a API do BCB responde; o SIDRA deve ser testado no início da M2.
