# `remy`: Meal weekly planner recommendation app for the lazy ones

This is the dev documents for the application

## Run everything locally

```bash
./start-all.sh            # auth backend :8010, Remy API :8081, frontend :3000
./start-all.sh --no-open  # same, without opening the browser
```

Logs from all three servers stream into one terminal, prefixed with the
service name. Ctrl+C stops all of them. Ports can be changed with
`BACKEND_PORT`, `API_PORT` and `FRONTEND_PORT`, for example
`BACKEND_PORT=8000 ./start-all.sh`.

The script expects `backend/.venv`, `api/.venv` and `frontend/node_modules` to
exist, PostgreSQL to be running, and `backend/.env` and `api/.env` to be filled
in.

If the backend or API port is held by a leftover Remy auth backend or Remy API
process, the script stops that process and carries on. It never stops anything
else: if a port is held by another program, by a frontend, or by an earlier
`./start-all.sh` that is still running, it exits without changing anything and
tells you what is using the port.
