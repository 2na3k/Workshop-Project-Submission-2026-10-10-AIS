# Finding: data-preparation dbt project fails to parse (price path)

- Date: 2026-10-05
- Severity: blocking (no dbt command in the project succeeds)
- Owner: data-preparation package maintainer (unassigned)
- Discovered by: p1 SDD effort, during phase p1's end-to-end verification
- Scope: out of scope for the p1 SDD effort; reported for the package owner

## Summary

The `remy-data-preparation` dbt project fails to parse. `dbt ls`, `dbt build`,
and any command that reads the project's models stop at a compilation error.
The failure is caused by `models/staging/stg_retail_listing.sql`, which reads
two nodes that no model, seed, or source produces.

## Evidence

Command:

    cd SystemCode/remy/data-preparation
    uv run --package remy-data-preparation dbt build --profiles-dir . --exclude tag:serving

Output (abridged):

    Compilation Error
      Model 'model.remy.stg_retail_listing'
      (models/staging/stg_retail_listing.sql) depends on a node named
      'retail_aisle_listing' which was not found

## Detail

`models/staging/stg_retail_listing.sql` unions two `ref(...)` targets:

- Line 17: `from {{ ref('retail_aisle_listing') }}`
- Line 31: `from {{ ref('retail_search_listing') }}`

Neither target exists as:

- a model under `models/` (no file named `retail_aisle_listing.sql` or
  `retail_search_listing.sql`),
- a seed under `seeds/` (the seed tree contains `13k-recipe/`,
  `central_food/`, `fairprice/price_mapped_nutrients.csv` — none named
  `retail_aisle_listing*` or `retail_search_listing*`),
- a source (no `sources.yml` in the project declares them).

The crawler package (`remy-data-crawler`) produces raw FairPrice listings
under different names and schemas:

- `src/data_crawler/data/output_raw/raw_matched_food_prices.csv`
  columns: `category, name, price_value, quantity, dietary`
- `src/data_crawler/data/output_raw/raw_unmatched_food_prices.csv`
  columns: `term, occurrences, rank, product_id, category, name, price_value,
  quantity, dietary`

The staging model expects a wider schema (`a, category, name, quantity,
price_value, dietary, origin, brand, variant, product` for the aisle branch;
`rank, term, product_id, category, name, quantity, price_value, dietary` for
the search branch). The enrichment that would produce those wider columns is
performed by `process_price.ipynb`, which writes
`data/output_final/price_mapped_nutrients.csv` (already a seed:
`seeds/fairprice/price_mapped_nutrients.csv`) — not
`retail_aisle_listing.csv` or `retail_search_listing.csv`.

Three models reference `stg_retail_listing`:

- `models/intermediate/int_product_identity.sql:6`
- `models/intermediate/int_price_fulfillment_candidates.sql:93`
- `models/mart/edge_fulfills.sql:125`

`models/staging/stg_price_mapped_nutrients.sql` reads the seed that does
exist (`price_mapped_nutrients`), but no downstream model consumes it. The
project therefore has two price paths: one wired (from
`stg_retail_listing`, whose inputs don't exist) and one orphaned (from
`stg_price_mapped_nutrients`, whose input exists).

## Impact

Any command that parses the project fails before reaching any model,
including:

- `dbt ls`
- `dbt build`
- `dbt run`
- `make dbt`, `make ci`, and any target that invokes dbt

This blocks the pipeline's end-to-end verification: no marts can be built,
no coverage report can be produced, and no reproducibility manifest can be
emitted from real data. Consumers that depend on the pipeline's output
(the graph load, the coverage report, downstream reasoning features) cannot
be verified against real data until the project parses.

## Suspected fix (for the package owner)

Two options:

1. **Produce the missing inputs.** If `retail_aisle_listing` and
   `retail_search_listing` were intended to exist as seeds or sources, add
   them (with the schema `stg_retail_listing.sql` expects). This preserves
   the current wiring.

2. **Rewire the price path.** Delete `stg_retail_listing.sql` and point
   `int_product_identity.sql` at `stg_price_mapped_nutrients` (the staging
   model that reads the seed that exists), then update
   `int_price_fulfillment_candidates.sql` and `edge_fulfills.sql` to consume
   the rewired chain. This removes the stale model and uses the data that is
   actually present.

Option 2 is likely the correct long-term shape: the notebook
(`process_price.ipynb`) already produces `price_mapped_nutrients.csv`, which
is checked in as a seed; the intermediate and mart models should read it.
The wider columns the current staging model expects (`origin`, `brand`,
`variant`, `product`) are produced by the notebook's enrichment and are
present in `price_mapped_nutrients.csv`; a rewire should preserve them.

## Relationship to phase p1 (SDD effort)

This finding is the root cause of the phase p1 deferrals recorded under the
name "O-1". O-1 was initially understood as "the data-preparation seeds are
missing"; the investigation shows the seeds are present and the block is a
stale model reference in the price path, owned by the data-preparation
package.

The p1 effort does not modify the data-preparation package. Its four
features (p1-001, p1-001b, p1-002, p1-003) are verified with fixture-based
evidence; the end-to-end pipeline demonstration is deferred to this finding's
resolution.

## References

- `SystemCode/remy/data-preparation/models/staging/stg_retail_listing.sql`
- `SystemCode/remy/data-preparation/models/staging/stg_price_mapped_nutrients.sql`
- `SystemCode/remy/data-preparation/models/intermediate/int_product_identity.sql`
- `SystemCode/remy/data-preparation/models/intermediate/int_price_fulfillment_candidates.sql`
- `SystemCode/remy/data-preparation/models/mart/edge_fulfills.sql`
- `SystemCode/remy/data-crawler/src/data_crawler/data/output_raw/`
- `SystemCode/remy/data-crawler/src/data_crawler/process_price.ipynb`
- `docs/sdd/phase-reviews/p1.md` (once written)
