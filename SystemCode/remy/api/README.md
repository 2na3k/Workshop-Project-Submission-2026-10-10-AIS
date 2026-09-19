# Remy API

From `SystemCode`, start the calculator API:

```bash
uv run --package remy-api uvicorn api.main:app --reload --port 8001
```

Open [Swagger UI](http://localhost:8001/docs) for interactive documentation.
Expand `POST /api/v1/calculate/cost-and-nutrition`, select **Try it out**, and
submit the chicken-and-oats example or your own ingredients.

- [OpenAPI JSON](http://localhost:8001/openapi.json)
- [ReDoc](http://localhost:8001/redoc)
- [Calculator contract and frontend examples](docs/calculate/calculate_api_doc.md)

Swagger includes request constraints, nutrient units, nullable cost fields,
per-ingredient warnings, and the shared error envelope for `400`, `422`, and `500`.
The contract's general `404` case concerns recipe/session lookups, which this
calculator endpoint does not perform.

This is the **Remy API** application (`api.main:app`). The separate **Remy Backend**
application (`remy/backend`, `main:app`) serves auth and preferences on port 8000;
its Swagger page does not contain calculator routes. Use port 8001 to run both.

Documentation can be viewed without connecting to Neo4j. Executing a calculation
requires a populated Neo4j database. Configure `NEO4J_URI`, `NEO4J_USERNAME`, and
`NEO4J_PASSWORD` in `SystemCode/.env` or `remy/api/.env` before starting the server.
