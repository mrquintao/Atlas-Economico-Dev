# ADR 0007 — Coleta automática por agendador próprio no Docker Compose

**Status:** aceito (2026-10-21), issue #6 (M4).

## Contexto

O `PROJECT_SPEC.md` (§3.3, §7) pede atualização automática dos dados com "scripts e agendamentos
simples", sem filas nem orquestradores, e sem serviços pagos. Até a M3 a coleta era manual (CLI por
indicador) ou via `scripts/ingest.sh` num cron do sistema, que parava no primeiro indicador com falha
(`set -e`) e não deixava o estado visível para quem consulta os dados.

## Decisões

1. **Lote único** (`app/ingestion/batch.py`, CLI `ingest --all`): todos os indicadores do catálogo,
   cada um isolado (a falha de um não impede os demais), com código de saída `1` se algum falhar.
2. **Agendador em processo próprio** (`app/ingestion/scheduler.py`), serviço opcional `scheduler` do
   Compose (perfil `scheduler`), com a mesma imagem da API. Horários em `INGEST_SCHEDULE`
   (`HH:MM[,HH:MM…]`) no fuso `America/Sao_Paulo`, o mesmo das datas das séries. Alternativas
   descartadas: cron dentro do contêiner (exige daemon extra, logs e fuso fora do controle da
   aplicação) e filas/Celery (vetadas pelo spec). O cron do sistema continua possível
   (`scripts/ingest.sh`, agora com `ingest --all`).
3. **Estado público da coleta**: `last_run` em cada indicador da API (status, horários e só o tipo do
   erro), exibido no painel de metodologia quando a última tentativa falhou ou está em andamento;
   `last_collected_at` continua sendo a última coleta **bem-sucedida**.
4. **Falha não pode parecer sucesso**: resposta vazia para intervalo que já tem dados gravados é falha;
   o 404 do gateway do BCB sem o corpo "Value(s) not found" do SGS é erro (antes virava "janela vazia");
   runs órfãos em `running` há mais de 1 hora são marcados como interrompidos.
5. `tzdata` passa a ser dependência explícita, para que `zoneinfo` funcione em imagens sem a base de
   fusos do sistema.

## Consequências

- Sem infraestrutura nova nem custo; o agendador não sobrevive a um host desligado: horários perdidos não
  são recuperados (mitigação: `INGEST_ON_START=true` ou execução manual).
- Não há trava contra duas coletas simultâneas do mesmo indicador (agendador e CLI manual); documentado
  como limitação, candidata a `pg_try_advisory_lock` se virar problema.
