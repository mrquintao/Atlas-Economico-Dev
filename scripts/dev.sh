#!/usr/bin/env bash
# Runs the Atlas Econômico Brasileiro locally with a single command.
#
#   scripts/dev.sh                 # local: API + web dev servers (Ctrl+C stops both)
#   scripts/dev.sh data            # incremental collection of the national indicators
#   scripts/dev.sh data --states 2025   # ... plus the state fiscal indicators of 2025 (slow)
#   scripts/dev.sh docker          # everything with Docker Compose
#   scripts/dev.sh --help
#
# The first run on an empty database collects the national indicators and the state
# boundaries from the official sources (a few minutes). Nothing is ever deleted.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/services/api"
WEB_DIR="$ROOT/apps/web"
LOG_DIR="$ROOT/.dev/logs"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

usage() {
  cat <<EOF
Uso: scripts/dev.sh [comando] [opções]

Comandos:
  up       (padrão) Prepara e executa localmente: verifica pré-requisitos e o PostgreSQL,
           cria os arquivos .env, instala dependências, aplica migrações, faz a primeira
           coleta num banco vazio e sobe a API (:$API_PORT) e o painel (:$WEB_PORT).
  data     Coleta incremental dos indicadores nacionais e da malha das UFs.
  docker   Sobe tudo com Docker Compose (db, api, web) e faz a primeira coleta.

Opções:
  --states ANO   Também coleta e deriva os indicadores fiscais estaduais do ANO (SICONFI,
                 limitado a 1 requisição/s: cerca de 10 minutos por ano).
  --no-data      Não faz a coleta automática da primeira execução.
  --db-docker    (up/data) Sobe só o PostgreSQL com Docker Compose, se ele não estiver acessível.
  -h, --help     Mostra esta ajuda.

Variáveis: API_PORT (padrão 8000), WEB_PORT (padrão 3000), DATABASE_URL (padrão: services/api/.env).
EOF
}

# ---------------------------------------------------------------- output helpers
if [[ -t 1 ]]; then
  BOLD=$'\e[1m' DIM=$'\e[2m' RED=$'\e[31m' GREEN=$'\e[32m' YELLOW=$'\e[33m' RESET=$'\e[0m'
else
  BOLD="" DIM="" RED="" GREEN="" YELLOW="" RESET=""
fi
step() { printf '%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok() { printf '%s  ✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%s  !%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die() {
  printf '%serro:%s %s\n' "$RED" "$RESET" "$*" >&2
  exit 1
}

# ---------------------------------------------------------------- arguments
COMMAND="up"
STATES_YEAR=""
NO_DATA=0
DB_DOCKER=0
if [[ $# -gt 0 && "$1" != -* ]]; then
  COMMAND="$1"
  shift
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --states)
      # Same bounds as `derive-fiscal --year` (SICONFI data from 2015 on).
      [[ $# -ge 2 && "$2" =~ ^[0-9]{4}$ && "$2" -ge 2015 && "$2" -le "$(date +%Y)" ]] ||
        die "--states exige um ano entre 2015 e $(date +%Y) (ex.: --states $(($(date +%Y) - 1)))"
      STATES_YEAR="$2"
      shift 2
      ;;
    --no-data) NO_DATA=1 && shift ;;
    --db-docker) DB_DOCKER=1 && shift ;;
    -h | --help) usage && exit 0 ;;
    *) die "opção desconhecida: $1 (use --help)" ;;
  esac
done
case "$COMMAND" in up | data | docker) ;; *) die "comando desconhecido: $COMMAND (use --help)" ;; esac
[[ "$NO_DATA" -eq 1 && "$COMMAND" == "data" ]] && die "--no-data não faz sentido com 'data' (o comando é a coleta)"
[[ "$NO_DATA" -eq 1 && -n "$STATES_YEAR" ]] && die "--no-data e --states são incompatíveis"
if [[ "$COMMAND" == "docker" ]]; then
  [[ "$DB_DOCKER" -eq 1 ]] && die "--db-docker vale para 'up' e 'data'; o modo 'docker' já sobe o banco"
  [[ "$API_PORT" != 8000 || "$WEB_PORT" != 3000 ]] &&
    die "o modo 'docker' usa as portas fixas 8000 e 3000 do docker-compose.yml (API_PORT/WEB_PORT valem só para 'up')"
fi

# ---------------------------------------------------------------- shared pieces
# Python run inside the API environment (local venv or the API container): prints the number
# of national observations and of stored state boundaries, to detect an empty database.
DATA_PROBE='
from sqlalchemy import text
from app.db.session import get_engine
with get_engine().connect() as conn:
    national = conn.execute(
        text(
            "SELECT count(*) FROM observations o JOIN geographic_units g"
            " ON g.id = o.geographic_unit_id WHERE g.geographic_level = :level"
        ),
        {"level": "country"},
    ).scalar_one()
    boundaries = conn.execute(text("SELECT count(*) FROM geographic_boundaries")).scalar_one()
print(national, boundaries)
'
DB_PROBE='
import sys
from app.core.config import get_settings
from app.db.session import get_engine
try:
    get_engine().connect().close()
except Exception as exc:
    url = get_settings().database_url
    print(f"{url.split(chr(64))[-1]}: {type(exc).__name__}: {str(exc).splitlines()[0]}", file=sys.stderr)
    sys.exit(1)
'

require() {
  command -v "$1" >/dev/null 2>&1 || die "$1 não encontrado. $2"
}

port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

# Runs a collection command (local or in the container); a failure is reported, not fatal:
# the application still starts and the gaps are shown as gaps. `data` exits non-zero if any failed.
FAILED_COLLECTIONS=0
RETRY_HINT="scripts/dev.sh data${STATES_YEAR:+ --states $STATES_YEAR}"
collect() {
  local label="$1"
  shift
  local log
  log="$LOG_DIR/$(date +%Y%m%d-%H%M%S)-$(printf '%s' "$label" | tr -cs 'A-Za-z0-9' '-' | sed 's/-$//').log"
  mkdir -p "$LOG_DIR"
  printf '%s  …%s %s %s(log: %s)%s\n' "$DIM" "$RESET" "$label" "$DIM" "${log#"$ROOT"/}" "$RESET"
  if "$@" >"$log" 2>&1; then
    ok "$label"
  else
    FAILED_COLLECTIONS=$((FAILED_COLLECTIONS + 1))
    warn "$label falhou (veja o log). A aplicação funciona com os dados já existentes; tente de novo com: $RETRY_HINT"
  fi
}

# ---------------------------------------------------------------- local mode
local_prerequisites() {
  step "Verificando pré-requisitos"
  require uv "Instale: https://docs.astral.sh/uv/getting-started/installation/"
  require node "Instale o Node.js 22: https://nodejs.org/"
  require npm "Ele acompanha o Node.js."
  local node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]')"
  [[ "$node_major" -ge 22 ]] || die "Node.js 22 ou mais recente é necessário (encontrado: $(node --version))."
  ok "uv $(uv --version | cut -d' ' -f2), Node.js $(node --version), npm $(npm --version)"
}

local_env_files() {
  step "Arquivos de configuração"
  if [[ ! -f "$API_DIR/.env" ]]; then
    cp "$ROOT/.env.example" "$API_DIR/.env"
    ok "services/api/.env criado a partir de .env.example"
  else
    ok "services/api/.env existente mantido"
  fi
  # For a manual `npm run dev`; this script always points the dashboard at the API it starts
  # (NEXT_PUBLIC_API_BASE_URL in the environment takes precedence over .env.local).
  if [[ ! -f "$WEB_DIR/.env.local" ]]; then
    printf 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000\n' >"$WEB_DIR/.env.local"
    ok "apps/web/.env.local criado"
  else
    ok "apps/web/.env.local existente mantido"
  fi
}

local_install() {
  step "Dependências"
  (cd "$API_DIR" && uv sync --frozen --quiet) || die "uv sync falhou"
  ok "backend (uv sync)"
  # npm ci only when node_modules is missing or older than the lockfile.
  if [[ ! -f "$WEB_DIR/node_modules/.package-lock.json" ||
    "$WEB_DIR/package-lock.json" -nt "$WEB_DIR/node_modules/.package-lock.json" ]]; then
    (cd "$WEB_DIR" && npm ci --no-audit --no-fund --loglevel=error) || die "npm ci falhou"
    ok "frontend (npm ci)"
  else
    ok "frontend (node_modules em dia)"
  fi
}

local_database() {
  step "Banco de dados"
  if ! (cd "$API_DIR" && uv run --frozen python -c "$DB_PROBE"); then
    if [[ "$DB_DOCKER" -eq 1 ]]; then
      require docker "Instale o Docker ou inicie um PostgreSQL 16 local."
      docker compose -f "$ROOT/docker-compose.yml" up -d --wait db >/dev/null || die "não foi possível subir o PostgreSQL com Docker"
      ok "PostgreSQL iniciado com Docker Compose (127.0.0.1:5432)"
      (cd "$API_DIR" && uv run --frozen python -c "$DB_PROBE") || die "PostgreSQL ainda inacessível"
    else
      die "PostgreSQL inacessível (DATABASE_URL do ambiente ou de services/api/.env).
       Opções: inicie seu PostgreSQL 16 e crie o banco (README, \"Opção B\"),
       ou rode: scripts/dev.sh --db-docker   (sobe só o banco com Docker Compose)"
    fi
  fi
  ok "PostgreSQL acessível"
  (cd "$API_DIR" && uv run --frozen alembic upgrade head >/dev/null 2>&1) ||
    die "falha ao aplicar as migrações (rode 'cd services/api && uv run alembic upgrade head' para ver o erro)"
  ok "migrações aplicadas"
}

# Runs the ingestion CLI / a Python snippet in the API environment ($RUNNER: local or docker).
api_cli() {
  if [[ "$RUNNER" == "docker" ]]; then
    docker compose -f "$ROOT/docker-compose.yml" exec -T api python -m app.ingestion.cli "$@"
  else
    (cd "$API_DIR" && LOG_JSON=false uv run --frozen python -m app.ingestion.cli "$@")
  fi
}

api_python() {
  if [[ "$RUNNER" == "docker" ]]; then
    docker compose -f "$ROOT/docker-compose.yml" exec -T api python -c "$1"
  else
    (cd "$API_DIR" && uv run --frozen python -c "$1")
  fi
}

load_data() {
  local mode="$1" # "first-run" or "update"
  if [[ "$mode" == "first-run" ]]; then
    [[ "$NO_DATA" -eq 1 ]] && return 0
    local counts national boundaries
    counts="$(api_python "$DATA_PROBE")" || die "não foi possível consultar o banco"
    read -r national boundaries <<<"$counts"
    if [[ "$national" -gt 0 && "$boundaries" -gt 0 && -z "$STATES_YEAR" ]]; then
      step "Dados"
      ok "banco já populado ($national observações nacionais); atualize com: scripts/dev.sh data"
      return 0
    fi
    step "Primeira coleta (fontes oficiais; alguns minutos)"
    [[ "$national" -eq 0 ]] && collect "indicadores nacionais" api_cli ingest --all
    [[ "$boundaries" -eq 0 ]] && collect "malha das UFs (IBGE)" api_cli ingest-boundaries
  else
    step "Coleta incremental (fontes oficiais)"
    collect "indicadores nacionais" api_cli ingest --all
    collect "malha das UFs (IBGE)" api_cli ingest-boundaries
  fi
  if [[ -n "$STATES_YEAR" ]]; then
    collect "indicadores fiscais estaduais de $STATES_YEAR (SICONFI, ~10 min)" \
      api_cli derive-fiscal --year "$STATES_YEAR" --collect
  elif [[ "$mode" == "first-run" ]]; then
    printf '%s  i%s Indicadores fiscais estaduais: scripts/dev.sh data --states %s\n' \
      "$DIM" "$RESET" "$(($(date +%Y) - 1))"
  fi
}

wait_http() {
  local url="$1" name="$2" seconds="$3"
  for _ in $(seq "$seconds"); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      ok "$name respondendo em $url"
      return 0
    fi
    sleep 1
  done
  return 1
}

PIDS=()
stop_services() {
  trap - INT TERM EXIT
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    printf '\n'
    step "Encerrando"
    for pid in "${PIDS[@]}"; do
      # Each service runs in its own process group: stop it with all its children.
      kill -TERM -- "-$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    ok "API e painel encerrados"
  fi
}

start_service() {
  local name="$1" dir="$2"
  shift 2
  # set -m gives the background job its own process group (pgid = its pid).
  set -m
  (cd "$dir" && exec "$@") > >(awk -v p="${DIM}[$name]${RESET} " '{ print p $0; fflush() }') 2>&1 &
  PIDS+=("$!")
  set +m
}

run_local() {
  local_prerequisites
  local_env_files
  local_install
  local_database
  if [[ "$COMMAND" == "data" ]]; then
    load_data update
    [[ "$FAILED_COLLECTIONS" -eq 0 ]] || die "$FAILED_COLLECTIONS coleta(s) falharam (veja os logs em .dev/logs/)"
    return 0
  fi
  load_data first-run

  step "Iniciando os servidores"
  port_in_use "$API_PORT" && die "a porta $API_PORT já está em uso (defina API_PORT=...)"
  port_in_use "$WEB_PORT" && die "a porta $WEB_PORT já está em uso (defina WEB_PORT=...)"
  trap 'stop_services; exit 130' INT
  trap 'stop_services; exit 143' TERM
  trap stop_services EXIT
  # Environment overrides services/api/.env: the dashboard origin must be allowed by CORS.
  start_service api "$API_DIR" env LOG_JSON=false \
    CORS_ORIGINS="[\"http://localhost:$WEB_PORT\",\"http://127.0.0.1:$WEB_PORT\"]" \
    uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"
  start_service web "$WEB_DIR" env NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE_URL="http://localhost:$API_PORT" \
    node_modules/.bin/next dev --port "$WEB_PORT"

  wait_http "http://127.0.0.1:$API_PORT/api/v1/health" "API" 60 || die "a API não respondeu em 60 s (veja as linhas [api] acima)"
  wait_http "http://localhost:$WEB_PORT" "Painel" 120 || die "o painel não respondeu em 120 s (veja as linhas [web] acima)"
  printf '\n%sAtlas Econômico Brasileiro em execução%s\n' "$BOLD" "$RESET"
  printf '  Painel:        http://localhost:%s   (estados em /estados)\n' "$WEB_PORT"
  printf '  API (OpenAPI): http://localhost:%s/docs\n' "$API_PORT"
  printf '  %sCtrl+C encerra os dois servidores.%s\n\n' "$DIM" "$RESET"
  # Stops everything as soon as either server exits (a loop instead of `wait -n PID...`,
  # which needs bash >= 5.1; macOS ships bash 3.2).
  while true; do
    for pid in "${PIDS[@]}"; do
      if ! kill -0 "$pid" 2>/dev/null; then
        warn "um dos servidores terminou; encerrando o outro"
        exit 1
      fi
    done
    sleep 1
  done
}

# ---------------------------------------------------------------- docker mode
run_docker() {
  step "Verificando pré-requisitos"
  require docker "Instale o Docker: https://docs.docker.com/get-docker/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 é necessário ('docker compose')."
  ok "$(docker compose version)"
  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    ok ".env criado a partir de .env.example"
  fi
  # Re-running with the stack already up just rebuilds/updates it; otherwise the ports must be free.
  if [[ -z "$(docker compose -f "$ROOT/docker-compose.yml" ps --status running -q api 2>/dev/null)" ]]; then
    port_in_use 8000 && die "a porta 8000 já está em uso"
    port_in_use 3000 && die "a porta 3000 já está em uso"
  fi

  step "Construindo e iniciando os containers (db, api, web)"
  docker compose -f "$ROOT/docker-compose.yml" up --build -d --wait ||
    die "falha ao iniciar o Compose (veja: docker compose logs)"
  ok "containers saudáveis"
  wait_http "http://127.0.0.1:8000/api/v1/health" "API" 60 || die "a API não respondeu"
  wait_http "http://localhost:3000" "Painel" 60 || die "o painel não respondeu"
  load_data first-run
  printf '\n%sAtlas Econômico Brasileiro em execução (Docker)%s\n' "$BOLD" "$RESET"
  printf '  Painel:        http://localhost:3000\n'
  printf '  API (OpenAPI): http://localhost:8000/docs\n'
  printf '  %sLogs: docker compose logs -f · Parar: docker compose down (os dados ficam no volume)%s\n' "$DIM" "$RESET"
}

if [[ "$COMMAND" == "docker" ]]; then
  RUNNER="docker"
  run_docker
else
  RUNNER="local"
  run_local
fi
