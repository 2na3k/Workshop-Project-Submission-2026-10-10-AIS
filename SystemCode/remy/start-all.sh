#!/usr/bin/env bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd -P)"
SYSTEM_ROOT="$(dirname "$ROOT")"
BACKEND_PORT="${BACKEND_PORT:-8010}"
API_PORT="${API_PORT:-8081}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
OPEN_BROWSER=1

usage() {
  cat <<EOF
Usage: ./start-all.sh [--no-open]

Builds and starts Remy with Docker Compose: PostgreSQL, the auth backend, the
Remy API and the Next.js frontend. Opens the frontend in your browser once
everything answers. Press Ctrl+C to stop and remove the containers; the
PostgreSQL data is kept in a Docker volume for the next run.

The API reads its Neo4j settings from api/.env and the auth backend reads
backend/.env (its database URL and CORS origins are set by Compose).

Ports can be changed with environment variables:
  BACKEND_PORT   auth backend   (default 8010)
  API_PORT       Remy API       (default 8081)
  FRONTEND_PORT  frontend       (default 3000)

Example: BACKEND_PORT=8000 ./start-all.sh --no-open
EOF
}

for arg in "$@"; do
  case "$arg" in
    --no-open) OPEN_BROWSER=0 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then
  BOLD=$'\033[1m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  BOLD=""; RED=""; GREEN=""; YELLOW=""; RESET=""
fi

info() { printf '%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok() { printf '%s ✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%s !%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
fail() { printf '%s ✗%s %s\n' "$RED" "$RESET" "$*" >&2; }

# Read by docker-compose.yml.
export BACKEND_PORT API_PORT FRONTEND_PORT
export REMY_API_ENV_FILE="$ROOT/api/.env"

compose() {
  docker compose --project-directory "$SYSTEM_ROOT" -f "$SYSTEM_ROOT/docker-compose.yml" "$@"
}

problems=0

if ! command -v docker >/dev/null; then
  fail "Docker is required. Install Docker Desktop: https://docs.docker.com/get-docker/"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is required (the \`docker compose\` command)."
  problems=1
fi
if ! docker info >/dev/null 2>&1; then
  fail "Docker is not running. Start Docker Desktop and try again."
  problems=1
fi
command -v curl >/dev/null || { fail "curl is required."; problems=1; }

if [ "$problems" -ne 0 ]; then
  exit 1
fi

if [ -n "$(compose ps --status running --quiet 2>/dev/null)" ]; then
  fail "Remy is already running in Docker."
  printf '   Press Ctrl+C in the terminal running ./start-all.sh, or run: (cd %q && docker compose down)\n' "$SYSTEM_ROOT" >&2
  exit 1
fi

# Docker's own port forwarder may hold a port for another container; Compose
# reports that clearly itself. Anything else (such as an old non-Docker run of
# the servers) is named here so it can be stopped.
if command -v lsof >/dev/null; then
  for spec in "$BACKEND_PORT:auth backend:BACKEND_PORT" "$API_PORT:Remy API:API_PORT" "$FRONTEND_PORT:frontend:FRONTEND_PORT"; do
    port=${spec%%:*}; rest=${spec#*:}; label=${rest%%:*}; var=${rest#*:}
    pids=""
    for pid in $(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u); do
      case "$(ps -ww -o command= -p "$pid" 2>/dev/null)" in
        *com.docker*|*vpnkit*|*docker-proxy*) ;;
        *) pids="$pids $pid" ;;
      esac
    done
    [ -n "$pids" ] || continue
    set -- $pids
    # Drop the directory from the program path so the useful part fits.
    cmd=$(ps -ww -o command= -p "$1" 2>/dev/null | sed 's#^[^ ]*/##' | cut -c1-70)
    fail "Port $port ($label) is in use by PID$( [ $# -gt 1 ] && echo s )$pids: $cmd"
    printf '   Stop it (an older ./start-all.sh without Docker?), or use another port: %s=<port> %s\n' "$var" "$0" >&2
    problems=1
  done
fi

if [ "$problems" -ne 0 ]; then
  exit 1
fi

[ -f "$ROOT/api/.env" ] || warn "api/.env not found. The API needs NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD."
[ -f "$ROOT/backend/.env" ] || warn "backend/.env not found, so the auth backend makes up a JWT secret on every start (see backend/.env.example)."

banner() {
  echo
  info "Remy is running"
  printf '    Frontend      http://localhost:%s\n' "$FRONTEND_PORT"
  printf '    Auth backend  http://localhost:%s/docs\n' "$BACKEND_PORT"
  printf '    Remy API      http://localhost:%s/docs\n' "$API_PORT"
  printf '    Live logs follow. Press Ctrl+C to stop everything.\n\n'
}

stop_all() {
  echo
  info "Stopping containers…"
  compose down >/dev/null 2>&1 && ok "All containers stopped."
}

interrupted=0
trap 'interrupted=1' INT TERM

info "Starting Remy in Docker (auth backend :$BACKEND_PORT, API :$API_PORT, frontend :$FRONTEND_PORT)"
info "The first run builds the images and takes a few minutes."

if ! compose up --build --detach --wait --wait-timeout 900 --remove-orphans; then
  if [ "$interrupted" -eq 0 ]; then
    echo
    fail "Remy did not start. The last log lines from each service:"
    compose ps --all
    compose logs --tail 30
  fi
  stop_all
  exit 1
fi
[ "$interrupted" -eq 0 ] || { stop_all; exit 130; }

banner
if [ "$OPEN_BROWSER" -eq 1 ]; then
  if command -v open >/dev/null; then
    open "http://localhost:$FRONTEND_PORT"
  elif command -v xdg-open >/dev/null; then
    xdg-open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1
  fi
fi

# `compose logs --follow` quits whenever a container is removed (for example a
# `docker compose run --rm`), so it is restarted rather than trusted as a
# sign that the stack has stopped.
follow_logs() {
  compose logs --follow --tail 0 &
  LOGS=$!
}
follow_logs

failed=0
while [ "$interrupted" -eq 0 ]; do
  stopped=$(compose ps --all --status exited --status dead --format '{{.Service}}' \
    postgres backend api frontend 2>/dev/null | tr '\n' ' ')
  if [ -n "${stopped// /}" ]; then
    fail "Stopped unexpectedly: $stopped. Shutting down the others."
    failed=1
    break
  fi
  kill -0 "$LOGS" 2>/dev/null || follow_logs
  sleep 2
done

kill "$LOGS" 2>/dev/null
wait "$LOGS" 2>/dev/null
stop_all
exit "$failed"
