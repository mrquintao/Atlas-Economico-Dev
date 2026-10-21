# Estado do desenvolvimento (checkpoint)

> Ler primeiro ao iniciar qualquer sessão. Atualizar ao fim de cada entrega ou quando surgir um bloqueio.
> Fonte das tarefas: GitHub Issues · Roadmap: [`../implementation-roadmap.md`](../implementation-roadmap.md)

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-21 |
| Fase atual | 2 — Atlas estadual (MVP nacional concluído: release `v0.1.0`) |
| Última entrega | S8 — comparação e ranking das UFs em `/estados/comparar` (issue #18, PR #46). Antes: S6 (#16, PR #45), S7 (#17, PRs #43 e #44), S5 (#15, PR #42), S4 (#14, PR #41), S3 (#13, PR #40), S2 (#12, PR #39), S1 (#11, PR #38) e [release `v0.1.0`](https://github.com/mrquintao/Atlas-Economico-Dev/releases/tag/v0.1.0) |
| Próxima entrega elegível | **S9 — release `v0.2.0` do Atlas estadual ([#19](https://github.com/mrquintao/Atlas-Economico-Dev/issues/19))** |
| Issue ativa | nenhuma (comentar na issue ao iniciar, para evitar sessões concorrentes) |
| Branch | novo branch a partir da `main` atualizada |
| Último commit integrado na `main` | merge do PR #46 (conferir com `git log origin/main -1`); tag `v0.1.0` em `ade5512` |
| Última validação | S8: `scripts/check.sh` verde (416 pytest, 155 vitest); E2E 31/31; ranking sobre coleta real de 2025 (RCL e DCL/RCL, 27 UFs) igual às amostras oficiais |

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

Iniciar a S9 (#19), release `v0.2.0` do Atlas estadual: verificar os critérios de aceite da Fase 2 com
evidências em `docs/releases/v0.2.0.md`, integrar por PR e disparar o workflow Release (AGENT_POLICY §7).
Valores per capita e em % do PIB estadual ficaram fora da S8 (exigem séries do IBGE com validação do
economist); registrar como limitação conhecida na release.

Concorrência: na S7, o mantenedor integrou o branch da sessão (PR #43) antes da auditoria; as
correções vieram no PR #44. Na S1, outra sessão disparou a release `v0.1.0` um minuto antes (a segunda
execução foi recusada pela trava de tag). Antes de começar, conferir branches e PRs abertos e
reivindicar a issue com um comentário.

Migração mais recente: `0009` (frequências `bimonthly`/`four_monthly` e seed dos 9 indicadores fiscais estaduais).

Achados menores pendentes (registrados nas issues/PRs): S8 — rodapé dos painéis de comparação sem
link de fonte nem data de coleta; `parse_selection` faz uma consulta por UF (até 27); sem teste unitário
do proxy (coberto pelo E2E). S7 — `/estados/mg/` faz dois 308; `grid.left`
fixo de 44 px pode cortar rótulos do eixo em R$ abaixo de 1 mi; fixture E2E sem bimestre faltante;
erro na recarga das séries estaduais mostra um aviso por painel. S5 — ~40–55 consultas por requisição em `/states/{uf}/…` (consolidar quando houver endpoint com as 27 UFs); nota do DF ausente em `/indicators/{code}/observations?geography=DF`. S4 — observação mantida quando uma retificação remove a linha de origem (ADR 0010); coleta falha interrompe `derive-fiscal --collect` sem derivar. S3 — `Retry-After` do 429 ignorado (backoff
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
  Bancos: `atlas` (dados reais, **não destruir**; recriado do zero na sessão da S8: migrado até 0009, com os anexos de 2025 do RREO 03 e RGF 02 das 27 UFs e `STATE_RCL`/`STATE_DCL_RCL` derivados; sem malha nem séries nacionais), `atlas_test` e `atlas_ci` (descartáveis).
- Validação local: `TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh`.
- E2E local: banco `atlas_e2e` com a fixture sintética (`docs/testing-e2e.md`), `npm run build` e
  `CI=1 DATABASE_URL=…/atlas_e2e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npm run test:e2e`.
- Não usar `pkill -f`/`pgrep -f` com padrões que casem com a própria linha de comando (derruba o shell).
- Docker: o daemon sobe (`dockerd &`), mas o proxy bloqueia os blobs do ghcr.io (imagem do uv); os
  Dockerfiles são validados pelo job `Docker Compose` do CI. `docker compose config` funciona localmente.
- Proxy de saída: as APIs do BCB e do SIDRA (`apisidra.ibge.gov.br`) respondem.
- Se `/tmp/pgdata` não existir (sessão nova), inicializar com `initdb -A trust` como `postgres`, criar o
  papel `atlas` e os bancos.
