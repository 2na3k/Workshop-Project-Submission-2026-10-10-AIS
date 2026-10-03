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

Starts the Remy auth backend, Remy API and Next.js frontend together,
then opens the frontend in your browser. Press Ctrl+C to stop all three.

If the backend or API port is still held by a leftover Remy auth backend or
Remy API process, that process is stopped first. Nothing else is ever stopped:
if a port is held by anything else, including a frontend or an earlier
./start-all.sh that is still running, the script exits and changes nothing.

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

descendants() {
  local child
  for child in $(pgrep -P "$1" 2>/dev/null); do
    echo "$child"
    descendants "$child"
  done
}

running() {
  local pid state
  for pid in "$@"; do
    state=$(ps -o stat= -p "$pid" 2>/dev/null)
    if [ -n "$state" ] && [ "${state#Z}" = "$state" ]; then
      echo "$pid"
    fi
  done
}

wait_gone() {
  local tries=$1 _
  shift
  for _ in $(seq "$tries"); do
    [ -z "$(running "$@")" ] && return 0
    sleep 0.5
  done
  [ -z "$(running "$@")" ]
}

stop_pids() {
  local targets="" pid
  for pid in "$@"; do
    targets="$targets $pid $(descendants "$pid")"
  done
  kill $targets 2>/dev/null
  wait_gone 10 $targets || kill -9 $(running $targets) 2>/dev/null
}

command_of() {
  ps -ww -o command= -p "$1" 2>/dev/null
}

parent_of() {
  ps -o ppid= -p "$1" 2>/dev/null | tr -d ' '
}

listeners() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | sort -u
}

cwd_of() {
  local cwd
  cwd=$(lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  [ -n "$cwd" ] && (cd "$cwd" 2>/dev/null && /bin/pwd -P)
}

script_run_of() {
  local pid run=""
  pid=$(parent_of "$1")
  while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
    case "$(basename "$(ps -o comm= -p "$pid" 2>/dev/null)")" in
      bash)
        case "$(command_of "$pid")" in
          *start-all.sh*) run=$pid ;;
        esac
        ;;
    esac
    pid=$(parent_of "$pid")
  done
  echo "$run"
}

remy_server_of() {
  local pid=$1 kind=$2 candidate cmd cwd
  for candidate in "$pid" "$(parent_of "$pid")"; do
    [ -n "$candidate" ] || continue
    cmd=$(command_of "$candidate")
    case "$cmd" in
      *uvicorn*) ;;
      *) continue ;;
    esac
    cwd=$(cwd_of "$candidate")
    if [ "$kind" = backend ]; then
      case "$cmd" in
        *api.main:app*) continue ;;
        *" main:app"*) ;;
        *) continue ;;
      esac
      case "$cwd/" in
        "$ROOT/backend/"*|"$SYSTEM_ROOT/") ;;
        *) continue ;;
      esac
    else
      case "$cmd" in
        *api.main:app*) ;;
        *) continue ;;
      esac
      case "$cwd/" in
        "$ROOT/"*|"$SYSTEM_ROOT/") ;;
        *) continue ;;
      esac
    fi
    echo "$candidate"
    return 0
  done
  return 1
}

add_unique() {
  case " $1 " in
    *" $2 "*) echo "$1" ;;
    *) echo "$1 $2" ;;
  esac
}

problems=0

require() {
  if [ ! -e "$1" ]; then
    fail "$2"
    problems=1
  fi
}

require "$ROOT/backend/.venv/bin/python" "Missing backend/.venv. See backend/README.md to create it."
require "$ROOT/api/.venv/bin/python" "Missing api/.venv. See api/README.md to create it."
require "$ROOT/frontend/node_modules" "Missing frontend/node_modules. Run: (cd frontend && npm install)"
command -v curl >/dev/null || { fail "curl is required."; problems=1; }
command -v lsof >/dev/null || { fail "lsof is required."; problems=1; }

if [ "$problems" -ne 0 ]; then
  exit 1
fi

SCRIPT_RUNS=""
SCRIPT_PORTS=""
TO_STOP=""
STOP_NOTES=""

check_port() {
  local port=$1 label=$2 var=$3 kind=$4 pid run server
  for pid in $(listeners "$port"); do
    run=$(script_run_of "$pid")
    if [ -n "$run" ]; then
      SCRIPT_RUNS=$(add_unique "$SCRIPT_RUNS" "$run")
      SCRIPT_PORTS=$(add_unique "$SCRIPT_PORTS" "$port")
    elif [ -n "$kind" ] && server=$(remy_server_of "$pid" "$kind"); then
      case " $TO_STOP " in
        *" $server "*) ;;
        *)
          TO_STOP="$TO_STOP $server"
          STOP_NOTES="$STOP_NOTES
Port $port is held by a leftover $label (PID $server). Stopping it."
          ;;
      esac
    else
      fail "Port $port ($label) is in use by PID $pid: $(command_of "$pid" | cut -c1-80)"
      printf '   The script will not stop it. Close it yourself, or use another port: %s=<port> %s\n' "$var" "$0" >&2
      problems=1
    fi
  done
}

check_port "$BACKEND_PORT" "auth backend" BACKEND_PORT backend
check_port "$API_PORT" "Remy API" API_PORT api
check_port "$FRONTEND_PORT" "frontend" FRONTEND_PORT ""

for run in $SCRIPT_RUNS; do
  fail "An earlier ./start-all.sh (PID $run) is still running on port(s)$(echo " $SCRIPT_PORTS" | tr -s ' ')."
  printf '   Press Ctrl+C in its terminal (or run: kill -INT %s), then try again.\n' "$run" >&2
  problems=1
done

if [ "$problems" -ne 0 ]; then
  exit 1
fi

if [ -n "$TO_STOP" ]; then
  echo "$STOP_NOTES" | while IFS= read -r note; do
    [ -n "$note" ] && warn "$note"
  done
  stop_pids $TO_STOP
  for port in "$BACKEND_PORT" "$API_PORT"; do
    for _ in $(seq 10); do
      [ -z "$(listeners "$port")" ] && break
      sleep 0.5
    done
    if [ -n "$(listeners "$port")" ]; then
      fail "Port $port is still in use after stopping the leftover server."
      exit 1
    fi
  done
fi

[ -f "$ROOT/backend/.env" ] || warn "backend/.env not found, so the auth backend uses its defaults (see backend/.env.example)."
[ -f "$ROOT/api/.env" ] || warn "api/.env not found. The API needs NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD."

db_url=$(grep -E '^REMY_DATABASE_URL=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2-)
if command -v pg_isready >/dev/null; then
  if [ -n "$db_url" ]; then
    pg_isready -q -d "$db_url" || warn "PostgreSQL is not accepting connections, so the auth backend will fail to start."
  else
    pg_isready -q || warn "PostgreSQL is not accepting connections, so the auth backend will fail to start."
  fi
fi

cors=$(grep -E '^REMY_CORS_ORIGINS=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2-)
cors="${REMY_CORS_ORIGINS:-${cors:-http://localhost:3000,http://localhost:3100}}"
case ",$cors," in
  *",http://localhost:$FRONTEND_PORT,"*) ;;
  *) cors="$cors,http://localhost:$FRONTEND_PORT" ;;
esac

NAMES=()
PIDS=()

stop_all() {
  trap - EXIT INT TERM
  [ ${#PIDS[@]} -gt 0 ] || return
  echo
  info "Stopping servers…"
  exec 2>/dev/null
  stop_pids "${PIDS[@]}"
  wait 2>/dev/null
  ok "All servers stopped."
}

trap stop_all EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

start() {
  local name=$1 color=$2 dir=$3 prefix
  shift 3
  if [ -n "$RESET" ]; then
    prefix=$(printf '\033[%sm%-8s\033[0m│ ' "$color" "$name")
  else
    prefix=$(printf '%-8s│ ' "$name")
  fi
  ( (cd "$dir" && exec "$@") 2>&1 | awk -v p="$prefix" '{ print p $0; fflush() }' ) &
  NAMES+=("$name")
  PIDS+=("$!")
}

wait_ready() {
  local index=$1 url=$2 label=$3 deadline=$((SECONDS + 120))
  while [ $SECONDS -lt $deadline ]; do
    if [ -z "$(running "${PIDS[$index]}")" ]; then
      fail "${NAMES[$index]} exited during startup. See its log lines above."
      exit 1
    fi
    if curl -fs -o /dev/null --max-time 2 "$url"; then
      ok "$label is up"
      return 0
    fi
    sleep 1
  done
  warn "${NAMES[$index]} is not answering at $url yet. Check its log lines above."
}

info "Starting Remy (auth backend :$BACKEND_PORT, API :$API_PORT, frontend :$FRONTEND_PORT)"

start backend 36 "$ROOT/backend/src" \
  env PYTHONUNBUFFERED=1 REMY_CORS_ORIGINS="$cors" \
  "$ROOT/backend/.venv/bin/python" -m uvicorn main:app --reload --port "$BACKEND_PORT"

start api 35 "$ROOT" \
  env PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/api/src:$ROOT/workflows/src:$ROOT/domain/src" \
  "$ROOT/api/.venv/bin/python" -m uvicorn api.main:app --reload --port "$API_PORT" \
  --reload-dir "$ROOT/api/src" --reload-dir "$ROOT/workflows/src" --reload-dir "$ROOT/domain/src"

start frontend 33 "$ROOT/frontend" \
  env NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" REMY_API_URL="http://localhost:$API_PORT" \
  npm run dev -- --port "$FRONTEND_PORT"

wait_ready 0 "http://localhost:$BACKEND_PORT/health" "Auth backend"
wait_ready 1 "http://localhost:$API_PORT/health" "Remy API"
wait_ready 2 "http://localhost:$FRONTEND_PORT/signin" "Frontend"

echo
info "Remy is running"
printf '    Frontend      http://localhost:%s\n' "$FRONTEND_PORT"
printf '    Auth backend  http://localhost:%s/docs\n' "$BACKEND_PORT"
printf '    Remy API      http://localhost:%s/docs\n' "$API_PORT"
printf '    Press Ctrl+C to stop everything.\n\n'

if [ "$OPEN_BROWSER" -eq 1 ]; then
  if command -v open >/dev/null; then
    open "http://localhost:$FRONTEND_PORT"
  elif command -v xdg-open >/dev/null; then
    xdg-open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1
  fi
fi

while true; do
  index=0
  while [ $index -lt ${#PIDS[@]} ]; do
    if [ -z "$(running "${PIDS[$index]}")" ]; then
      fail "${NAMES[$index]} stopped unexpectedly. Shutting down the others."
      exit 1
    fi
    index=$((index + 1))
  done
  sleep 1
done
