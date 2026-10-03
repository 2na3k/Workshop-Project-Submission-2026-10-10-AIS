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
