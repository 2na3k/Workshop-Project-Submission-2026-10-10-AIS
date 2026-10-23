# Remy component prompts

Each file contains a standalone copy-paste requirements prompt with project
context, component responsibilities, interfaces, acceptance criteria, and a
VERIFICATION section with concrete technical checks and expected evidence.
Open a file and copy its fenced prompt; no other prompt is required as a preface.
These are requirements briefs, not service startup instructions.

| # | Prompt | Component location |
| --- | --- | --- |
| 1 | [Web frontend](01-web-frontend.md) | SystemCode/remy/frontend |
| 2 | [Account and user-data backend](02-account-backend.md) | SystemCode/remy/backend |
| 3 | [Recommendation API](03-recommendation-api.md) | SystemCode/remy/api |
| 4 | [Conversational application](04-chat-application.md) | SystemCode/remy/app |
| 5 | [Conversational workflow](05-conversational-workflow.md) | SystemCode/remy/workflows |
| 6 | [Shared domain](06-shared-domain.md) | SystemCode/remy/domain |
| 7 | [Data collection](07-data-collection.md) | SystemCode/remy/data-crawler |
| 8 | [Data preparation](08-data-preparation.md) | SystemCode/remy/data-preparation |
| 9 | [Neo4j graph](09-neo4j-graph.md) | SystemCode/docs/neo4j_db_design.md and SystemCode/remy/data-preparation/models/serving |
| 10 | [Application PostgreSQL](10-application-postgres.md) | SystemCode/remy/backend/db.sql and SystemCode/remy/api/src/api/core/database.py |
| 11 | [DuckDB and DuckLake](11-duckdb-ducklake.md) | SystemCode/remy/data-preparation/profiles.yml and SystemCode/remy/data-preparation/models |
| 12 | [Observability and optional evaluation](12-observability-evaluation.md) | SystemCode/docker-compose.yml, SystemCode/remy/api/src/api/core, and SystemCode/remy/api/src/api/features/plan |
| 13 | [System integration](13-system-integration.md) | Cross-component contracts and the complete user journey |

Use an individual prompt for a component-specific brief. Use the integration
prompt when defining or reconciling the boundaries between components.
