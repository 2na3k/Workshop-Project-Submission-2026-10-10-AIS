# Remy data preparation

The dbt project builds the food and recipe staging/mart models with DuckDB and DuckLake.

## Setup

1. Download the data from [Google Drive](https://drive.google.com/drive/folders/1Gvgsyn0SwnXeCXB457-B1KTeu11VjmrI?usp=sharing).
2. Put the downloaded data in `remy/data-preparation/seeds` so the files include:

   ```text
   seeds/13k-recipe/13k-recipes.csv
   seeds/central_food/branded_food.csv
   seeds/central_food/food.csv
   seeds/central_food/food_component.csv
   seeds/central_food/food_nutrient/data.parquet
   seeds/fairprice/price_mapped_nutrients.csv
   ```

   Refresh the FairPrice mapping from the crawler output when needed:

   ```bash
   cp remy/data-crawler/src/data_crawler/data/output_final/price_mapped_nutrients.csv \
      remy/data-preparation/seeds/fairprice/price_mapped_nutrients.csv
   ```

3. From `SystemCode`, install dependencies and run dbt:

   ```bash
   make install
   make dbt
   ```

The `seeds` directory is ignored by Git. Non-production is the default. Use `DBT_TARGET=prod make dbt` for production. For an isolated validation build, set all three paths and create their parent directories first:

```bash
export DBT_NONPROD_PATH=target/lean-validation/db.duckdb
export DBT_NONPROD_DUCKLAKE_CATALOG=target/lean-validation/ducklake/catalog.sqlite
export DBT_NONPROD_DUCKLAKE_DATA=target/lean-validation/ducklake/data
mkdir -p "$(dirname "$DBT_NONPROD_PATH")" "$(dirname "$DBT_NONPROD_DUCKLAKE_CATALOG")" "$DBT_NONPROD_DUCKLAKE_DATA"
uv run dbt build --exclude tag:serving
```

Run the query-time estimate without writing Neo4j:

```bash
uv run python scripts/recipe_estimate.py 882 --assumed-servings 2 --requested-portions 1 --halal-mode off
```

Add `--require-cost` when cost completeness is required. Results remain partial when any mandatory choice, quantity, conversion, evidence, or matching package basis is unresolved.

## Serve to Neo4j

The `recipe_graph_to_neo4j` Python model reads the seven built mart relations, writes them to Neo4j, and materializes the loaded row counts in the serving schema.

Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `SystemCode/.env.nonprod` (or `.env.prod` with `DBT_TARGET=prod`), then build everything and load Neo4j in one shot:

```bash
make dbt-all
```

To synchronize already-built marts, withdrawing stale projection-owned facts before loading:

```bash
make serve-neo4j
```

Synchronization is deliberately replacement-only and transactional. Before the first load over a legacy ownerless projection, back it up and perform a reviewed one-time migration that either removes the legacy projection or assigns `projection_owner = 'remy_recipe_graph'` only to verified Remy nodes and relationships. The loader never deletes ownerless data automatically.

`make serve-neo4j-replace` remains an alias for `make serve-neo4j`.
