# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 1 — MVP nacional |
| Última entrega | M2 — IPCA 12 meses (issue #4), PR #30: conector IBGE/SIDRA, ingestão genérica por fonte, cartão e terceiro gráfico sincronizado, quebras de linha em períodos ausentes |
| Próxima entrega elegível | **M3 — `GET /api/v1/dashboard/national` ([#5](https://github.com/mrquintao/Atlas-Economico-Dev/issues/5))** |
| Issue ativa | nenhuma até o início da M3 |
| Branch | novo branch a partir da `main` atualizada |
| Último commit integrado na `main` | merge do PR #30 (`93decf8`; conferir com `git log origin/main -1`) |
| Última validação | M2: `scripts/check.sh` (144 pytest com PostgreSQL, 51 vitest, lint, format, `alembic check`, typecheck, build); coleta real do IPCA (550 meses, idempotente) conferida 100% contra o SIDRA; navegador desktop e mobile com dados reais, console limpo; qa-auditor sem críticos, achados importantes corrigidos |

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

Iniciar a M3 (#5): endpoint `GET /api/v1/dashboard/national` com o resumo dos três indicadores
(último valor, mês/dia de referência, variação em 12 meses em p.p., fonte e metadados), reutilizando
`latestFromMonthly`/estatísticas do backend; depois M4 (#6), automação da coleta.

Achados menores da auditoria da M2 deixados para depois (registrados no PR): resposta vazia do SIDRA conta
como sucesso, igual ao SGS (avaliar alerta na M4, monitoramento); lacunas de vários meses recebem uma
única quebra no gráfico (o cursor cai no ponto real mais próximo); "Todo o histórico" começa em 1980 por
causa do IPCA.

## Ambiente de desenvolvimento (lembrete para sessões em nuvem)

- PostgreSQL 16 local: `/usr/lib/postgresql/16/bin`, dados em `/tmp/pgdata` (sobrevive a reinícios;
  após um reboot: `su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pgdata/log -o '-p 5432 -k /tmp' start"`).
  Bancos: `atlas` (dados reais, **não destruir**; migrado até 0005), `atlas_test` e `atlas_ci` (descartáveis).
- Validação local: `TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh`.
- Sem Docker local: os Dockerfiles são validados pelo job `Docker Compose` do CI.
- Proxy de saída: as APIs do BCB e do SIDRA (`apisidra.ibge.gov.br`) respondem.
- Se `/tmp/pgdata` não existir (sessão nova), inicializar com `initdb -A trust` como `postgres`, criar o
  papel `atlas` e os bancos.
