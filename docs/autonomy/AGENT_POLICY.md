# Política de desenvolvimento autônomo

Autorização do mantenedor (2026-10-21): o agente principal executa autonomamente decisões técnicas
rotineiras, issues, implementação, testes, PRs e **merges**, desde que os gates de qualidade abaixo
sejam satisfeitos. Este documento prevalece sobre instruções genéricas de ferramentas, mas não sobre
o `PROJECT_SPEC.md` nem sobre as proibições abaixo.

## 1. Ciclo por entrega

1. Ler [`STATE.md`](STATE.md) e sincronizar a `main` (`git fetch && git merge --ff-only`).
2. Pegar a **próxima issue elegível**: a primeira do [roadmap](../implementation-roadmap.md) com
   `autonomous:yes`, sem `agent:blocked` e com as dependências fechadas.
3. Criar o branch a partir da `main` atualizada (`feat/<issue>-<slug>` ou `fix/<issue>-<slug>`; o branch
   de sessão designado pelo ambiente pode ser usado no lugar, desde que parta da `main` atual).
4. Implementar verticalmente (dados → API → UI → docs), com testes, consultando os agentes (§5).
5. Validar localmente **a partir de um clone limpo** com `scripts/check.sh` (lint, format, migrações,
   testes, typecheck e build: os mesmos gates dos jobs API e Web do CI).
6. Validar dados contra a fonte oficial (amostras registradas na documentação).
7. Pedir auditoria adversarial ao `qa-auditor`; corrigir os achados críticos e altos; corrigir os médios
   ou registrar a decisão (no PR ou em ADR); corrigir ou registrar na issue os baixos; repetir a
   validação e a auditoria quando houver correção relevante.
8. Fazer commits pequenos, abrir o PR para a `main` com `Closes #N`, aguardar o CI e integrar (§3).
9. Atualizar `STATE.md`, `RUN_LOG.md`, o roadmap e a issue.

Não iniciar outra entrega enquanto a atual puder ser concluída com os recursos disponíveis.

## 2. Proibições permanentes

- Force push, rebase/amend de commits publicados ou qualquer reescrita do histórico publicado.
- Push direto na `main` (toda mudança entra por PR).
- Commit de credenciais, tokens, chaves ou arquivos `.env`.
- Bypass de verificações obrigatórias; desativar, pular ou enfraquecer testes ou critérios de aceite para
  obter CI verde.
- Alterações destrutivas em bancos com dados reais (`DROP`, `TRUNCATE`, `DELETE` em massa, `--full` que
  apague dados). Bancos de teste descartáveis são permitidos.
- Infraestrutura ou serviços pagos (hospedagem etc.) sem orçamento autorizado.
- **Qualquer funcionalidade do produto baseada em LLM** (decisão permanente, ADR 0004): assistentes ou
  consultas em linguagem natural, chatbots, integrações com APIs de LLM, RAG, embeddings e bancos
  vetoriais, e análises ou relatórios gerados por modelo. Nenhuma dependência desse tipo em
  `services/api` ou `apps/web`. Funcionalidades removidas por essa decisão não são substituídas
  automaticamente por outras.
- Implantação pública de funcionalidade incompleta.
- Alterar permissões ou configurações de segurança para contornar falhas.
- Funcionalidades fora das três fases sem justificativa registrada em ADR.

## 3. Gate de integração (merge autônomo)

Um PR só é integrado quando **todos** os itens valem para o commit mais recente do PR:

1. O PR aponta para a `main` e seus commits correspondem à issue planejada.
2. Os checks obrigatórios estão concluídos e com `success`:
   - `API (lint, migrations, tests)`;
   - `Web (lint, typecheck, tests, build)`;
   - `Docker Compose (build and smoke test)`;
   - `E2E (Playwright)`.
   Checks ausentes, pendentes, `skipped` ou `cancelled` **não** contam como aprovação.
3. O PR está mergeável (sem conflitos; `mergeable_state` limpo).
4. Não há achado crítico, alto ou médio do `qa-auditor` sem correção ou decisão registrada (no PR ou
   em ADR), nem thread de revisão sem resposta. Achados baixos são corrigidos ou registrados na issue.
5. O estado é revalidado imediatamente antes do merge, que é feito com `expectedHeadSha` igual ao
   commit verificado.

Mecanismo: o auto-merge nativo do GitHub, quando a proteção de branch estiver configurada (issue I1).
Até lá, o agente aplica o gate acima e faz o merge com `merge_pull_request` (método `merge`, que
preserva o histórico). Depois do merge: sincronizar a `main`, fechar a issue e registrar o resultado.

## 4. Falhas

- Analisar os logs, identificar a causa raiz, corrigir o problema real, revalidar e registrar no `RUN_LOG`.
- "Flake" não é causa: um re-run só para confirmar uma falha de infraestrutura, no máximo uma vez.
- Após **três tentativas substancialmente distintas** sem progresso: aplicar `agent:blocked` na issue,
  registrar as evidências em `STATE.md` e na issue, e seguir para a próxima issue independente.
- Nunca relatar erro como sucesso; nunca entrar em ciclos de alterações sem hipótese nova.

## 5. Agentes especializados

| Agente | Uso obrigatório |
|---|---|
| `economist` | Toda série nova: metadados, unidade, metodologia, regras de agregação, amostras oficiais |
| `data-engineer` | Conectores e ingestão complexos (ex.: SICONFI), modelagem e migrações |
| `fullstack-developer` | Partes extensas de API/UI que possam ser feitas em paralelo |
| `qa-auditor` | Antes de todo PR: auditoria adversarial independente (inclui verificar que nenhuma dependência ou funcionalidade de LLM entrou no produto) |

O agente principal integra as contribuições e responde por elas. Agentes que editam arquivos trabalham
em worktrees isolados ou sobre arquivos disjuntos; nunca dois agentes no mesmo arquivo ou branch ao mesmo tempo.

## 6. Git e identidade

- Commits com a identidade do mantenedor (aplicada por `scripts/configure-git-identity.sh`), sem
  trailers de coautoria (`.claude/settings.json`).
- Mensagens em inglês, no imperativo, com o escopo (`feat(api): …`, `fix(web): …`, `docs: …`).
- Merge commits (sem squash) para preservar o histórico auditável.

## 7. Releases

Ao concluir um marco (M7, S9, A8): verificar os critérios de aceite da fase, criar a tag `vX.Y.Z` na
`main` e publicar as release notes. Nenhuma publicação em hospedagem pública faz parte das releases de código.

## 8. Bloqueios conhecidos de recursos

Registrados em [`STATE.md`](STATE.md). Ex.: proteção de branch e GitHub Projects não são configuráveis com
as ferramentas do agente (exigem ação do mantenedor).
