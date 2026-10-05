# Running Remy with Docker Compose

This guide starts the whole app (database, auth backend, Remy API and web
frontend) in Docker with one command. All commands run from `SystemCode/`.

## What runs

| Service    | What it is                     | Open on your machine            | Health check   |
|------------|--------------------------------|---------------------------------|----------------|
| `postgres` | PostgreSQL 17, user accounts   | not exposed                     | `pg_isready`   |
| `backend`  | Auth backend (FastAPI)         | http://localhost:8010/docs      | `GET /health`  |
| `api`      | Remy API: plans and calculator | http://localhost:8081/docs      | `GET /health`  |
| `frontend` | Next.js web app                | http://localhost:3000           | `GET /signin`  |

They start in order: `postgres` → `backend` and `api` → `frontend`. Each one
waits until the services it needs are healthy.

The API uses the Neo4j database set in `remy/api/.env` (for example Neo4j
Aura). The local `neo4j` container and the data jobs are not started; see
[Local Neo4j and data jobs](#local-neo4j-and-data-jobs).

## Before you start

1. **Docker Desktop** (or Docker Engine with Compose v2) is installed and
   running. Check with `docker compose version`.
2. **`remy/api/.env`** exists with the Neo4j connection:

   ```dotenv
   NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
   NEO4J_USERNAME=<username>
   NEO4J_PASSWORD=<password>
   NEO4J_DATABASE=<database>
   ```

3. **`remy/backend/.env`** exists with a signing secret for sign-in sessions
   and the database password, which the database and the backend share:

   ```dotenv
   REMY_JWT_SECRET=<output of: openssl rand -base64 48>
   POSTGRES_PASSWORD=<output of: openssl rand -hex 24>
   ```

   Without it the backend invents a new secret on every start, so everyone is
   signed out whenever it restarts. Compose sets the backend's database URL and
   CORS origins itself, so values for those in this file are ignored.

4. **Ports 8010, 8081 and 3000 are free.** Stop any copy of the servers you
   started outside Docker, or [use other ports](#change-the-ports).

Both `.env` files are git-ignored and are never copied into the images.

## Build and start it

### With Docker Compose

```bash
docker compose build         # build the images
docker compose up -d --wait  # start everything, return once all are healthy
```

The first build takes a few minutes; later builds reuse the cache and only
redo what changed. `docker compose up --build -d --wait` does both steps in
one command. Leave out `-d` to keep the logs in the terminal, where **Ctrl+C**
stops everything. Stop a background start with `docker compose down`.

### With the script

```bash
./remy/start-all.sh            # opens the browser when everything is ready
./remy/start-all.sh --no-open  # same, without opening the browser
```

The script checks that Docker is running and the ports are free, runs the
build and start above, prints the URLs, then streams the logs of all services.
**Ctrl+C** stops and removes the containers.

## Check that it works

```bash
docker compose ps
```

Every service should show `(healthy)` in its STATUS. `(health: starting)`
means it is still booting; give it a minute.

Then, in a browser, open http://localhost:3000, sign up and build a plan. Or
check from the terminal:

```bash
curl http://localhost:8010/health    # auth backend: {"status":"ok",...}
curl http://localhost:8081/health    # Remy API

# Calculator, through the frontend's /api/v1 proxy (needs Neo4j)
curl -X POST http://localhost:3000/api/v1/calculate/cost-and-nutrition \
  -H 'Content-Type: application/json' \
  -d '{"servings":1,"ingredients":[{"name":"Tomatoes","quantity":100,"unit":"g"}]}'

# Plan stream: progress events, then text, then the plan
curl -N -X POST http://localhost:3000/api/v1/plan \
  -H 'Content-Type: application/json' -H 'Accept: text/event-stream' \
  -d '{"horizon_days":3,"meals_per_day":3}'
```

## Everyday commands

| Task                                   | Command                                          |
|----------------------------------------|--------------------------------------------------|
| See status                             | `docker compose ps`                              |
| Follow all logs                        | `docker compose logs -f`                         |
| Follow one service                     | `docker compose logs -f api`                     |
| Restart one service                    | `docker compose restart api`                     |
| Rebuild and restart one service        | `docker compose up --build -d api`               |
| Open a shell in the database (asks for `POSTGRES_PASSWORD`) | `docker compose exec postgres psql -U remy -d remy_main` |
| Stop and remove containers (keep data) | `docker compose down`                            |
| Stop and also delete the database      | `docker compose down -v`                         |

The containers run the code that was in the images when they were built, so
there is no hot reload. After changing code, run the start command again (it
rebuilds) or use `docker compose up --build -d <service>`. For hot reload while
developing one service, run that service outside Docker as described in its
own README.

## Change the ports

Set any of these when starting:

```bash
BACKEND_PORT=18010 API_PORT=18081 FRONTEND_PORT=13000 ./remy/start-all.sh
```

The same works in front of `docker compose up --build -d --wait`. Keep
`--build` whenever you change `BACKEND_PORT`: the frontend image has the
backend's address built in.

## Settings

Compose reads these from your shell or from `SystemCode/.env`:

| Variable                 | Default        | Used for                                         |
|--------------------------|----------------|--------------------------------------------------|
| `BACKEND_PORT`           | `8010`         | Auth backend port on your machine                |
| `API_PORT`               | `8081`         | Remy API port on your machine                    |
| `FRONTEND_PORT`          | `3000`         | Web app port on your machine                     |
| `REMY_API_ENV_FILE`      | `remy/api/.env` | File with the API's Neo4j settings (the Makefile uses `.env.nonprod`) |

## The database

User accounts and preferences are stored in the `remy_postgres_data` Docker
volume, so they survive `docker compose down` and restarts.

`remy/backend/db.sql` creates the schema the **first** time, when the volume is
empty. Later edits to `db.sql` are not applied to an existing volume. To start
over with the new schema (this deletes all accounts):

```bash
docker compose down -v
```

Accounts from a PostgreSQL running outside Docker are not copied in.

## Troubleshooting

**`postgres` exits with "superuser password is not specified".**
Set `POSTGRES_PASSWORD` in `remy/backend/.env`.
See [Before you start](#before-you-start).

**`backend` is unhealthy with "password authentication failed".** The password
in `remy/backend/.env` differs from the one the database was created with; the
database keeps its first password. Put the old password back, or recreate the
database (this deletes all accounts) with `docker compose down -v`.

**"port is already allocated" or the script says a port is in use.**
Something else is listening there, often the servers started without Docker.
Stop it, or [change the ports](#change-the-ports).

**`api` is unhealthy, or plans and the calculator return errors.**
Check the Neo4j settings in `remy/api/.env`, then read the error with
`docker compose logs api`.

**`backend` keeps restarting.** Look at `docker compose logs postgres` and
`docker compose logs backend`. If `db.sql` changed recently, see
[The database](#the-database).

**The web app cannot sign in after changing `BACKEND_PORT`.** The frontend
still points at the old port. Start again with `--build`.

**Everyone is signed out after a restart.** Set `REMY_JWT_SECRET` in
`remy/backend/.env`.

**The script says Remy is already running in Docker.** Another copy is still
running. Press Ctrl+C in its terminal, or run `docker compose down`.

## Local Neo4j and data jobs

These are for the data pipeline and are only started on request, through
Compose profiles:

```bash
make up       # API with a local Neo4j, settings from .env.nonprod
make up-all   # everything, including the local Neo4j and the data jobs
```

The local Neo4j needs `NEO4J_PASSWORD` set in `.env.nonprod`. See the
`SystemCode` README and `remy/data-preparation/README.md` for the pipeline.
