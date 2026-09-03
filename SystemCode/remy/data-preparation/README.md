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
   ```

3. From `SystemCode`, install dependencies and run dbt:

   ```bash
   make install
   make dbt
   ```

The `seeds` directory is ignored by Git. Non-production is the default. Use `DBT_TARGET=prod make dbt` for production, or override database files with `DBT_NONPROD_PATH` and `DBT_PROD_PATH`.

## Serve to Neo4j

The `recipe_graph_to_neo4j` Python model reads the seven built mart relations, writes them to Neo4j, and materializes the loaded row counts in the serving schema.

Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `SystemCode/.env.nonprod` (or `.env.prod` with `DBT_TARGET=prod`), then build everything and load Neo4j in one shot:

```bash
make dbt-all
```

To load already-built marts only:

```bash
make serve-neo4j
```

Replace the existing recipe graph projection before loading:

```bash
make serve-neo4j-replace
```
