# Auditoria de segurança pré-publicação

**Escopo da revisão:** estado da `main` no commit `25154805ba2276b53f06fc5ef756f4531460ea7b` (PR #28 integrado). Revisão realizada em outubro de 2026, antes da mudança de visibilidade do repositório.

## Resultado

**Nenhum segredo de produção confirmado foi encontrado na inspeção realizada.** Isto não constitui certificação de ausência de segredos: a varredura foi feita pela API do GitHub, sem acesso a um clone local completo nem execução de ferramentas dedicadas como Gitleaks/TruffleHog.

## Cobertura efetivamente verificada

- Árvore Git da `main`: 177 entradas, sem caminhos evidentes de credenciais privadas versionadas (ex.: `.env` real, `id_rsa`, `*.pem` ou `*.p12`).
- Histórico alcançável da `main`: **26 commits**, com inspeção de diffs textuais adicionados e removidos. No total, os commits informaram **399 ocorrências de arquivos alterados** (incluindo alterações repetidas nos mesmos arquivos).
- Referências existentes: duas branches (`main` e `claude/compassionate-mayer-eon3qz`, inicialmente no mesmo commit) e heads dos PRs #1, #2 e #28, que pertencem ao histórico inspecionado.
- Textos retornados da busca de **25 issues** e **3 Pull Requests**, examinados para indicadores de credenciais.
- Arquivos de configuração revisados individualmente: `.env.example`, `.gitignore`, `.dockerignore`, `.claude/settings.json`, `docker-compose.yml`, Dockerfiles, configuração do backend, CI, scripts operacionais e documentação de autonomia.

### Padrões procurados

Chaves privadas PEM; tokens GitHub; identificadores de access key AWS; chaves de API Google; chaves OpenAI/Anthropic; tokens Stripe e Slack; JWTs com estrutura típica; atribuições comuns a `password`, `token`, `secret` e `api_key`; e URIs com credenciais embutidas.

Os alertas encontrados para URIs com usuário/senha se referem às credenciais demonstrativas `atlas/atlas` no PostgreSQL local e à interpolação de variáveis no Compose, não a credenciais de produção identificadas.

## Alterações desta entrega

1. `LICENSE`: licença MIT, copyright 2026 Mateus Quintão.
2. `docker-compose.yml`: porta do PostgreSQL vinculada a `127.0.0.1:5432`, em vez de todas as interfaces de rede. A API continua acessando o serviço `db` na rede interna do Compose.
3. `README.md`: esclarecimento de que as credenciais padronizadas são apenas para desenvolvimento e de que a publicação da porta do banco é restrita ao loopback.

## Limites e riscos residuais

- Os arquivos binários existentes (favicon e capturas de tela) não passaram por análise binária ou inspeção de metadados com esta ferramenta; as capturas devem ser conferidas visualmente antes da publicação.
- Dados em arquivos locais **não versionados** (como `.env`), sistemas externos, credenciais armazenadas em GitHub Secrets e commits inalcançáveis pelas referências atuais não puderam ser auditados.
- A busca textual/regex pode deixar passar credenciais de formatos desconhecidos ou segredos sem nomenclatura típica.
- `atlas/atlas` é propositalmente uma credencial **de desenvolvimento**. Nunca usar esses valores em hospedagem pública. O `docker-compose.yml` é um ambiente local, não um manifesto de implantação de produção.
- Publicar o repositório também torna visíveis o histórico Git, nomes de autoria, discussões, documentação dos agentes, issues e PRs. Revisar conteúdo pessoal antes de alterar a visibilidade.
- Proteger `main` com checks obrigatórios (issue #10) antes de depender de merges totalmente automáticos.

## Verificação adicional recomendada antes de tornar público

Em um **clone local completo** do repositório, executar um detector dedicado que cubra o histórico, por exemplo, uma versão atualizada de Gitleaks:

```bash
gitleaks git --redact --verbose .
```

Inspecionar manualmente as capturas de tela e ativar secret scanning/push protection do GitHub conforme disponível. Se um segredo real for encontrado, **revogá-lo/rotacioná-lo**; removê-lo apenas da versão atual do arquivo não o elimina do histórico.

**Conclusão:** a inspeção remota não identificou credenciais reais, e os ajustes de licença e isolamento local do PostgreSQL estão preparados. O relatório não deve ser interpretado como garantia absoluta de segurança ou autorização automática para publicar ambientes de produção.
