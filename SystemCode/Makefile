SHELL := /bin/sh

UV ?= uv
COMPOSE ?= docker compose --env-file .env.nonprod
API_PACKAGE := remy-api
CRAWLER_PACKAGE := remy-data-crawler
DBT_PACKAGE := remy-data-preparation
DBT_TARGET ?= nonprod

-include .env.$(DBT_TARGET)
export NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD NEO4J_DATABASE NEO4J_HTTP NEO4J_USER NEO4J_BATCH_SIZE \
       AURA_INSTANCEID AURA_INSTANCENAME

.PHONY: help install sync lock check build build-all up up-all down logs \
        api crawler dbt dbt-all serve-neo4j serve-neo4j-replace frontend-install clean _neo4j-creds

help:
	@printf '%s\n' \
		'make install          Install all Python workspace dependencies' \
		'make lock             Resolve and update uv.lock' \
		'make check            Verify uv.lock is current' \
		'make api              Run the API locally with reload' \
		'make crawler          Run the crawler module' \
		'make dbt              Build dbt models except the Neo4j serving model' \
		'make dbt-all          Build dbt models, then load them into Neo4j' \
		'make serve-neo4j      Load built marts into Neo4j' \
		'make serve-neo4j-replace  Replace the existing Neo4j recipe graph' \
		'make build            Build the API image' \
		'make build-all        Build API, jobs, and optional frontend images' \
		'make up               Start API and Neo4j' \
		'make up-all           Start all Compose profiles' \
		'make down             Stop Compose services' \
		'make logs             Follow Compose logs'

install: sync

sync:
	$(UV) sync --all-packages

lock:
	$(UV) lock

check:
	$(UV) lock --check

api:
	$(UV) run --package $(API_PACKAGE) uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

crawler:
	$(UV) run --package $(CRAWLER_PACKAGE) python -m data_crawler

dbt:
	cd remy/data-preparation && mkdir -p target/$(DBT_TARGET)/staging target/$(DBT_TARGET)/ducklake/data && \
		DBT_TARGET=$(DBT_TARGET) $(UV) run --package $(DBT_PACKAGE) dbt build --profiles-dir . --exclude tag:serving

_neo4j-creds:
	@test -n "$(NEO4J_PASSWORD)" || { echo "Set NEO4J_PASSWORD or add it to .env.$(DBT_TARGET)"; exit 1; }

dbt-all: _neo4j-creds
	$(MAKE) dbt DBT_TARGET=$(DBT_TARGET)
	$(MAKE) serve-neo4j DBT_TARGET=$(DBT_TARGET)

serve-neo4j: _neo4j-creds
	cd remy/data-preparation && DBT_TARGET=$(DBT_TARGET) $(UV) run --package $(DBT_PACKAGE) dbt run --profiles-dir . --select recipe_graph_to_neo4j

serve-neo4j-replace: _neo4j-creds
	cd remy/data-preparation && DBT_TARGET=$(DBT_TARGET) NEO4J_REPLACE=true $(UV) run --package $(DBT_PACKAGE) dbt run --profiles-dir . --select recipe_graph_to_neo4j

build:
	$(COMPOSE) build api

build-all:
	$(COMPOSE) --profile frontend --profile jobs build

up:
	$(COMPOSE) up --build api neo4j

up-all:
	$(COMPOSE) --profile frontend --profile jobs up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

frontend-install:
	@test -f remy/app/package.json || { echo 'remy/app/package.json is not initialized yet'; exit 1; }
	npm --prefix remy/app install

clean:
	rm -rf .venv
