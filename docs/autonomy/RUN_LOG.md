# Registro de execuções

Entradas curtas, da mais recente para a mais antiga: o que foi entregue, o que foi validado, as falhas e
como foram corrigidas, e as decisões relevantes. Os detalhes ficam nos PRs, nas issues e nos ADRs.

## 2026-10-21 — Decisão de escopo: exclusão de funcionalidades com LLM (ADR 0004)

- Decisão permanente do mantenedor: o produto não terá funcionalidades baseadas em LLM.
- Atualizados: `PROJECT_SPEC.md` (§3, §19, §23, §24, com nota no topo), `CLAUDE.md` (regra 9), roadmap,
  AGENT_POLICY e STATE; ADR 0004 registrado.
- Backlog: issue #26 (A7) fechada como *not planned*; #27 (v1.0.0) passa a depender de A1–A6.
- Desenvolvimento autônomo retomado na M1 (#3).

## 2026-10-21 — Ativação da autonomia e M1 (issue #3)

- Orquestração criada: roadmap, AGENT_POLICY, DEFINITION_OF_DONE, STATE e este log; `CLAUDE.md`
  atualizado com a política de merge autônomo condicionado aos gates.
- Backlog no GitHub: issues #3–#27 (Fases 1–3, I1 de infraestrutura), com labels `phase:*`, `type:*`,
  `priority:*`, `autonomous:yes` e `agent:blocked`.
- Bloqueios registrados: proteção de branch e auto-merge nativo (#10) e GitHub Projects.
- M1 em andamento (detalhes no PR).

## 2026-10-21 — PR #2: DBGG/PIB (SGS 13762) e gráficos sincronizados

- Coleta real de 237 pontos conferida integralmente contra a API oficial; recoleta integral das séries
  mensais (revisões do PIB).
- Falhas corrigidas antes do merge: recursão infinita entre `echarts.connect` e a sincronização manual;
  cursor associando o mês seguinte (38 casos em 5 anos); zoom dessincronizado após redesenho.
- CI verde na 1ª execução; integrado pelo mantenedor.

## 2026-10-21 — PR #1: fundação e meta Selic (SGS 432)

- Conector BCB com janelas de 1 ano (as de 10 anos estouravam o timeout); ingestão idempotente e atômica.
- Falhas corrigidas: "hoje" calculado em UTC gravava D+1 (achado do qa-auditor); `rowcount = -1` no
  insert multi-linha; `public/` não versionado quebraria o Docker; typecheck dependia de `.next/` local.
- Identidade Git do mantenedor e desativação da coautoria configuradas; CI com 3 jobs.
