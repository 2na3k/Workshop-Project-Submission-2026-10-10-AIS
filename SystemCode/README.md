# Remy

Smart weekly meal-planning monorepo.

## Structure

- `remy/api` — backend API
- `remy/app` — frontend
- `remy/data-crawler` — data collection job
- `remy/data-preparation` — dbt transformations and Neo4j loader
- `remy/workflows` — recommendation workflows

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose
- Git LFS for the dbt seed data

## Setup

Run from `SystemCode`:

```bash
git lfs pull
make install
```

Environment files are local and not committed:

- `.env.nonprod` — local Docker development
- `.env.prod` — production services

Neo4j requires `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`.

## Common commands

```bash
make help          # list commands
make up            # start the API and local Neo4j
make down          # stop containers
make dbt           # build and test dbt models
make dbt-all       # build dbt models and load Neo4j
make api           # run the API locally
make crawler       # run the crawler
```

Use production configuration explicitly:

```bash
make dbt-all DBT_TARGET=prod
```

See `remy/data-preparation/README.md` for dbt and Neo4j details.
