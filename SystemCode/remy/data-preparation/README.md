# Data preparation

This dbt project transforms recipe, FoodData Central, and FairPrice data in DuckDB/DuckLake, then loads the curated recipe graph into Neo4j.

## Setup

From `SystemCode`:

1. Download the seed data from [Google Drive](https://drive.google.com/drive/folders/1Gvgsyn0SwnXeCXB457-B1KTeu11VjmrI?usp=sharing).
2. Place it under `remy/data-preparation/seeds` with these files:

   ```text
   13k-recipe/13k-recipes.csv
   central_food/branded_food.csv
   central_food/food.csv
   central_food/food_component.csv
   central_food/food_nutrient/data.parquet
   fairprice/price_mapped_nutrients.csv
   ```

3. Install dependencies and build the models:

   ```bash
   make install
   make dbt
   ```

The default target is `nonprod`; use `DBT_TARGET=prod make dbt` for production.

## Reproducibility manifest

`reproducibility/source_registry.json` is the declaration boundary for the
three consumed snapshots: FoodData Central, the recipe dataset, and FairPrice
listings. Every entry names its landed path, pinned snapshot id, and a JSON
capture/freeze record containing an ISO-8601 `observation_timestamp`. Missing,
empty, unreadable, or invalidly timestamped inputs fail closed; the build clock
and filesystem modification time are never used as fallbacks.

After dbt succeeds, `make dbt` emits
`target/<target>/source_snapshot_manifest.json`. It contains streamed SHA-256
source checksums and canonical, deterministically ordered checksums for the
seven graph marts plus `graph_quality_manifest`. Run
`DBT_TARGET=nonprod make reproducibility-check` to compare that manifest with
the reviewed values in `reproducibility/expected_checksums.json`.

To refresh the pinned values after an intentional, reviewed reference build,
copy the resulting mart `content_checksum` values into
`expected_checksums.json`, retain its schema versions, and record the reference
change in the feature close decisions. The normal check never rewrites pinned
values automatically. `make reproducible-build` runs dbt, manifest generation,
and the checker in order; `make ci` is the configured CI entry point.

## Manifest input and fail-closed refresh (p1-002, AC-1 through AC-10)

The serving model (`models/serving/recipe_graph_to_neo4j.py`) requires an
**accepted source snapshot manifest** before opening a Neo4j session. Pass it
explicitly via the environment:

```bash
NEO4J_SOURCE_MANIFEST=target/nonprod/source_snapshot_manifest.json \
  make serve-neo4j DBT_TARGET=nonprod
```

The `Makefile` (`serve-neo4j` target) passes this path automatically when
`reproducible-manifest` has produced it. If the manifest is missing, malformed,
or reports a failed quality/allocation result, the loader exits non-zero
before any graph mutation (`fail-closed`, R-15). The manifest's `sources`
section must list all three required identities (`FoodData Central`,
`recipe dataset`, `FairPrice listings`) with non-empty `snapshot_id` and
`content_checksum`, and its `marts` section must declare deterministic
`row_count` values that match the quality result.

Run the full verification locally:

```bash
make ci DBT_TARGET=nonprod
```

This runs `reproducible-build` (dbt + manifest + checker) followed by the
Python test layer (`tests/test_serving_model.py`, `tests/graph/test_edge_provenance.py`).
The dbt singular test (`tests/mart_edge_provenance.sql`) executes under
`dbt build`; its execution is blocked by p1-001 O-1 (missing seeds) and is
recorded as deferred in the feature plan.

## Common commands

```bash
make dbt-all       # Build dbt models and load Neo4j
make serve-neo4j   # Load already-built marts into Neo4j
```

Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `SystemCode/.env.nonprod` (or `.env.prod`) before loading Neo4j.

Run a recipe cost and nutrition estimate without Neo4j:

```bash
uv run --package remy-data-preparation \
  python remy/data-preparation/scripts/recipe_estimate.py 882 \
  --assumed-servings 2 --requested-portions 1 --halal-mode off
```

## Testing

The test suite lives under `tests/` and uses pytest. It has two layers.

### Fake driver (`fake_driver`)

`tests/conftest.py` provides a `fake_driver` fixture that emulates the
Neo4j driver/session/result surface the serving model
(`models/serving/recipe_graph_to_neo4j.py`) uses. It records every
`run(cypher, **params)` as an ordered `(cypher, params)` list, so tests can
assert on the statements the model issues without a live database. These tests
run anywhere and are the default.

### Cloud Neo4j integration (`neo4j_driver`)

`tests/graph/` holds integration tests marked `@pytest.mark.integration`. They
connect to a **dedicated** cloud Neo4j test instance. The `neo4j_driver`
fixture builds a driver, runs `MATCH (n) DETACH DELETE n` before each test, and
closes the driver afterwards.

> The instance must be dedicated to testing: the fixture wipes the whole
> database between tests. Never point these at the development / production
> Neo4j configured in `.env.nonprod`.

The fixture reads three variables — `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`,
`NEO4J_TEST_PASSWORD` — from the process environment first, then from a
gitignored `.env.test` file at the **repository root** (the directory holding
`.git`, which the fixture resolves with `git rev-parse --show-toplevel`).
Copy the example there and fill in the dedicated test credentials:

```bash
# from the repository root
cp SystemCode/remy/data-preparation/.env.test.example .env.test
```

#### Skip versus fail

- **Local run, instance not configured:** the integration tests **skip**. Run
  the unit layer only with:

  ```bash
  uv run --package remy-data-preparation pytest -q tests -m "not integration"
  ```

- **CI run (`CI=1`/`true`/`yes`), instance not configured:** the integration
  tests **fail** rather than skip, so a missing `NEO4J_TEST_*` secret cannot
  turn the job silently green. The `.github/workflows/data-preparation.yml`
  job runs `pytest -m "not integration"` first, then `pytest -m integration`
  with `CI=true` and the three variables injected from repository secrets.
- **Locally exporting `CI=1`** turns the skips into failures, which is how the
  CI behaviour can be reproduced before pushing.
