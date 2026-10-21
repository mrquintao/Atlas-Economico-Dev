# Definição de pronto (DoD)

Uma entrega só é considerada concluída quando todos os itens aplicáveis abaixo são verdadeiros e
verificáveis. "N/A" deve ser justificado no PR.

## Código
- [ ] Implementação vertical completa do escopo da issue (sem TODOs que bloqueiem o uso).
- [ ] Tipagem explícita (Python e TypeScript `strict`, sem `any`); sem código morto.
- [ ] Valores econômicos em `NUMERIC`/`Decimal`; datas ISO 8601; unidades explícitas na API.
- [ ] Nenhum segredo no código ou no histórico.
- [ ] Nenhuma funcionalidade ou dependência baseada em LLM (SDKs de LLM, embeddings, bancos vetoriais),
      conforme o ADR 0004; análises e textos do produto são determinísticos e versionados.

## Testes
- [ ] Testes novos para cada regra crítica (parsing, conversões, filtros, agregações, idempotência,
      erros), incluindo um **teste de regressão** para cada bug corrigido, que falhe sem a correção.
- [ ] Testes sem rede: `httpx.MockTransport` e fixtures locais; fixtures reais identificadas.
- [ ] `pytest` com PostgreSQL (`REQUIRE_DB_TESTS=1`) e `vitest` passando.

## Qualidade e integração
- [ ] `ruff check`, `ruff format --check`, `npm run lint`, `npm run typecheck`, `npm run build` sem erros.
- [ ] Migrações: upgrade → downgrade → upgrade sem erros (quando houver migração).
- [ ] Validação a partir de um clone limpo (o estado local não pode mascarar falhas).
- [ ] CI verde no commit final do PR (API, Web, E2E e Docker).

## Dados e metodologia (séries novas ou alteradas)
- [ ] Metadados validados pelo `economist` contra a fonte oficial (nome, unidade, frequência, início,
      metodologia, link oficial).
- [ ] Coleta real executada e reexecutada (idempotência demonstrada).
- [ ] Pelo menos 5 amostras conferidas contra a fonte oficial, registradas em `docs/indicators.md`.
- [ ] Nenhum valor inventado, interpolado ou zero no lugar de ausência.

## Interface (quando houver UI)
- [ ] Estados de carregamento, erro (com nova tentativa) e vazio.
- [ ] Formatação pt-BR; variações de taxas em p.p.
- [ ] Acessibilidade: rótulos, teclado, contraste, informação que não depende só de cor.
- [ ] Verificação no navegador (desktop e mobile) sem erros no console.

## Documentação e rastreabilidade
- [ ] README e `docs/` atualizados; ADR para cada decisão arquitetural relevante.
- [ ] Auditoria do `qa-auditor` sem achados críticos ou altos em aberto.
- [ ] PR com `Closes #N`, resumo e validações; issue fechada após o merge.
- [ ] `STATE.md`, `RUN_LOG.md` e roadmap atualizados.
