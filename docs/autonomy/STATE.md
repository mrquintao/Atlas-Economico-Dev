# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 2 — Atlas estadual (MVP nacional concluído: `v0.1.0`) |
| Última entrega | M7 — verificação do §25 com evidências (`docs/releases/v0.1.0.md`) e release `v0.1.0` (issue #9, PR #36) pelo novo workflow `Release` |
| Próxima entrega elegível | **S1 — unidades geográficas: 27 UFs e 5 regiões com códigos IBGE validados ([#11](https://github.com/mrquintao/Atlas-Economico-Dev/issues/11))** |
| Issue ativa | nenhuma até o início da S1 |
| Branch | novo branch a partir da `main` atualizada |
| Último commit integrado na `main` | merge do PR #36 (conferir com `git log origin/main -1`); tag `v0.1.0` |
| Última validação | M7: execução do README (Opção B) em clone limpo com banco novo e coleta real (10.093/237/550), recoleta sem duplicações, 15 amostras = fonte oficial (DBGG integral), navegador claro/escuro/mobile sem erros, contraste da navegação 7,58:1; `scripts/check.sh` e CI da `main` verdes |

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

Confirmar a release `v0.1.0` no GitHub (workflow `Release`). Depois, iniciar a Fase 2 pela S1 (#11):
27 UFs e 5 regiões com códigos IBGE validados contra a API de localidades do IBGE (economist +
data-engineer), via migração de seed.

Achados menores pendentes (registrados nas issues/PRs): M2 — lacunas de vários meses recebem uma única
quebra no gráfico; "Todo o histórico" começa em 1980 por causa do IPCA. M3 — em erro da requisição única
do dashboard, cada cartão mostra seu próprio "Tentar novamente" (mesmo padrão dos gráficos); a variação
"em 12 meses" de série diária compara com o fechamento do mesmo mês do ano anterior (documentado em
`docs/api.md`; mudar a regra exige decisão do economist). M4 — horários perdidos do agendador não são
recuperados; sem trava contra coletas simultâneas do mesmo indicador (ADR 0007, limitações). M5 — achados
baixos na issue #7 (foco nas âncoras internas, nome do site sem link; contraste medido na M7: 7,58:1, ok).
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
