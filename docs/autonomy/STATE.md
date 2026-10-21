# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 2 — Atlas estadual (MVP nacional concluído: release `v0.1.0`) |
| Última entrega | S4 — indicadores fiscais estaduais derivados do SICONFI (9 indicadores `STATE_*`, migração 0009, CLI `derive-fiscal`, ADR 0010, issue #14, PR #41). Antes: S3 (#13, PR #40), S2 (#12, PR #39), S1 (#11, PR #38) e [release `v0.1.0`](https://github.com/mrquintao/Atlas-Economico-Dev/releases/tag/v0.1.0) |
| Próxima entrega elegível | **S5 — API estadual `/states/{uf}/indicators` e `/states/{uf}/dashboard` ([#15](https://github.com/mrquintao/Atlas-Economico-Dev/issues/15))**; os dados vêm de `derive-fiscal` (ver `docs/state-fiscal-indicators.md`) |
| Issue ativa | nenhuma (comentar na issue ao iniciar, para evitar sessões concorrentes) |
| Branch | novo branch a partir da `main` atualizada |
| Último commit integrado na `main` | merge do PR #41 (conferir com `git log origin/main -1`); tag `v0.1.0` em `ade5512` |
| Última validação | S4: coleta real de 2025 para as 27 UFs (5 anexos) e derivação: 1.053 observações, 0 lacunas/ambiguidades, reexecução idempotente; 54 amostras do economist + 5 conferências independentes na API sem divergência; `scripts/check.sh` verde (348 pytest, 73 vitest); E2E local 11/11 |

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

Iniciar a S5 (#15): endpoints estaduais sobre os indicadores `STATE_*` (já servidos por
`/indicators/{code}/observations?geography=UF`). Para ter dados locais: `derive-fiscal --year 2025
--collect` (≈ 15 min a 1 req/s; outros anos idem). Regras a respeitar na API/UI: fluxos acumulados no
ano (`year_to_date` em `fiscal_catalog.py`) não têm estatísticas entre períodos; ressalva do DF em
comparações; lacunas nunca como zero. Antes de pôr o SICONFI no agendador, criar trava entre
processos. Atenção: códigos e siglas do IBGE são únicos só por nível (`1` = Brasil e Norte; `SE` =
Sergipe e Sudeste).

Concorrência: na sessão da S1, outra sessão disparou a release `v0.1.0` um minuto antes (a segunda
execução foi recusada pela trava de tag). Antes de começar, conferir branches e PRs abertos e
reivindicar a issue com um comentário.

Migração mais recente: `0009` (frequências `bimonthly`/`four_monthly` e seed dos 9 indicadores fiscais estaduais).

Achados menores pendentes (registrados nas issues/PRs): S4 — observação mantida quando uma retificação remove a linha de origem (ADR 0010); coleta falha interrompe `derive-fiscal --collect` sem derivar. S3 — `Retry-After` do 429 ignorado (backoff
já mais lento que o limite); coleta do SICONFI manual, fora do agendador; limitador de taxa por processo.
S2 — a malha só é coletada manualmente
(`ingest-boundaries`), fora do agendador; edições não publicadas pelo IBGE respondem 500 e passam
pelas tentativas de retry (a mensagem final avisa). M2 — lacunas de vários meses recebem uma única
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
  Bancos: `atlas` (dados reais, **não destruir**; na sessão da S4 o cluster foi recriado do zero: `atlas` migrado até 0009, com os anexos de 2025 das 27 UFs e os indicadores `STATE_*` derivados, sem séries nacionais nem malha), `atlas_test` e `atlas_ci` (descartáveis).
- Validação local: `TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh`.
- E2E local: banco `atlas_e2e` com a fixture sintética (`docs/testing-e2e.md`), `npm run build` e
  `CI=1 DATABASE_URL=…/atlas_e2e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npm run test:e2e`.
- Não usar `pkill -f`/`pgrep -f` com padrões que casem com a própria linha de comando (derruba o shell).
- Docker: o daemon sobe (`dockerd &`), mas o proxy bloqueia os blobs do ghcr.io (imagem do uv); os
  Dockerfiles são validados pelo job `Docker Compose` do CI. `docker compose config` funciona localmente.
- Proxy de saída: as APIs do BCB e do SIDRA (`apisidra.ibge.gov.br`) respondem.
- Se `/tmp/pgdata` não existir (sessão nova), inicializar com `initdb -A trust` como `postgres`, criar o
  papel `atlas` e os bancos.
