# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 1 — MVP nacional |
| Última entrega | M6 — testes E2E com Playwright (issue #8), PR #35: 11 testes do fluxo principal sobre fixture sintética protegida, job `E2E (Playwright)` no CI e no gate de merge (ADR 0008) |
| Próxima entrega elegível | **M7 — verificação dos critérios de aceite do MVP e release `v0.1.0` ([#9](https://github.com/mrquintao/Atlas-Economico-Dev/issues/9))** |
| Issue ativa | nenhuma até o início da M7 |
| Branch | novo branch a partir da `main` atualizada |
| Último commit integrado na `main` | merge do PR #35 (conferir com `git log origin/main -1`) |
| Última validação | M6: `scripts/check.sh` em clone limpo (193→201 pytest, 72 vitest, lint, format, `alembic check`, typecheck, build); E2E 11/11 em 3 execuções locais seguidas e verde no CI em 3 commits consecutivos; mutações de `chart-sync.ts` detectadas pelos testes correspondentes |

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

Iniciar a M7 (#9): conferir os critérios de aceite do MVP (`PROJECT_SPEC.md` §25) contra o sistema
implementado, registrar evidências e preparar a release `v0.1.0` (tag + release notes; sem publicação
em hospedagem pública). Na M7, medir também o contraste da navegação (achado baixo da M5, #7).

Achados menores pendentes (registrados nas issues/PRs): M2 — lacunas de vários meses recebem uma única
quebra no gráfico; "Todo o histórico" começa em 1980 por causa do IPCA. M3 — em erro da requisição única
do dashboard, cada cartão mostra seu próprio "Tentar novamente" (mesmo padrão dos gráficos); a variação
"em 12 meses" de série diária compara com o fechamento do mesmo mês do ano anterior (documentado em
`docs/api.md`; mudar a regra exige decisão do economist). M4 — horários perdidos do agendador não são
recuperados; sem trava contra coletas simultâneas do mesmo indicador (ADR 0007, limitações). M5 — achados
baixos na issue #7 (foco nas âncoras internas, contraste da navegação a medir na M7, nome do site sem link).
M6 — o E2E roda com `next start`, não com o servidor `standalone` da imagem; a topologia do Compose
segue coberta só pelo smoke test do job Docker (ADR 0008).

## Ambiente de desenvolvimento (lembrete para sessões em nuvem)

- PostgreSQL 16 local: `/usr/lib/postgresql/16/bin`, dados em `/tmp/pgdata` (sobrevive a reinícios;
  após um reboot: `su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pgdata/log -o '-p 5432 -k /tmp' start"`).
  Bancos: `atlas` (dados reais, **não destruir**; migrado até 0005; recriado na sessão da M5 com coleta real dos 3 indicadores), `atlas_test` e `atlas_ci` (descartáveis).
- Validação local: `TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh`.
- E2E local: banco `atlas_e2e` com a fixture sintética (`docs/testing-e2e.md`), `npm run build` e
  `CI=1 DATABASE_URL=…/atlas_e2e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npm run test:e2e`.
- Não usar `pkill -f`/`pgrep -f` com padrões que casem com a própria linha de comando (derruba o shell).
- Docker: o daemon sobe (`dockerd &`), mas o proxy bloqueia os blobs do ghcr.io (imagem do uv); os
  Dockerfiles são validados pelo job `Docker Compose` do CI. `docker compose config` funciona localmente.
- Proxy de saída: as APIs do BCB e do SIDRA (`apisidra.ibge.gov.br`) respondem.
- Se `/tmp/pgdata` não existir (sessão nova), inicializar com `initdb -A trust` como `postgres`, criar o
  papel `atlas` e os bancos.
