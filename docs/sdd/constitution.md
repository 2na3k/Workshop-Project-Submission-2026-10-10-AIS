# Project Constitution

Version: 1.0
Status: approved

Long-lived, project-level. Changes only via `amendments/`. This file has no
changelog; `amendments/` is the changelog.

## Hierarchy

constitution > approved amendments > specs > plans > deployed implementation.
Where this file is silent, lower layers decide. Where this file speaks, lower
layers must comply or the constitution must be amended.

## Stack & architecture

### R-1 Single schema, no dual support
- Rule: The repository's schema names are the single source of truth. When
  documentation and the deployed schema disagree, the documentation is corrected
  in the same change — never carried in parallel. No code path may accept two
  names for the same concept.
- Why: Proposal source-precedence; the deployed graph and the design doc had
  divergent names and supporting both was rejected.
- Check: Named test fixture — `tests/graph/test_schema_conformance.py` asserts
  the property names used by the repository match a single canonical schema list,
  and fails if the repository accepts more than one name for the same concept.

### R-2 Inward dependency direction
- Rule: In the FastAPI backend, imports must flow inward (router → service →
  repository → models). Features must not import each other's internals; cross-
  feature use goes through a feature's public API. The `domain` layer is a leaf,
  `workflows` must not depend on `api`, and `api` must not depend on `app`.
- Why: Tech stack / FastAPI structure doc.
- Check: CI command — `uv run lint-imports` with the `.importlinter` contracts
  ("domain is a leaf", "workflows does not depend on api", "api does not depend
  on app") passes.

### R-3 Stack shape is fixed unless amended
- Rule: The backend is a Python web service; the data layer is a columnar
  lakehouse built from declarative transformations; the serving layer is a graph
  store; the plan solver is a constraint solver. Introducing a different *shape* —
  a non-Python backend, a row-store data layer, a relational serving layer, or a
  heuristic solver — requires an amendment. Version bumps and same-shape
  substitutions do not.
- Why: System design, database design, and tech stack docs; the rest of this
  constitution assumes these shapes.
- Check: CI command — `uv run python -c "import fastapi, duckdb, neo4j; from
  ortools.sat.python import cp_model"` succeeds. A reviewer rejects a PR that adds
  a parallel framework, store, or solver.

### R-4 Graph provenance preserved on every linking record
- Rule: Every linking record must preserve provenance — source, source ID /
  snapshot, mapping confidence, mapping/normalization version, and freshness
  timestamp — on the `REQUIRES` and `FULFILLS` edges that connect recipes, food
  concepts, nutrition profiles, and offers.
- Why: Proposal G-4, G-7; Neo4j design doc.
- Check: Named test fixture — `tests/graph/test_edge_provenance.py` writes a
  populated `REQUIRES` and `FULFILLS` edge through the code path that creates them
  and asserts every provenance property is non-null on read.

## Reasoning safety

### R-5 Absent evidence drops, never includes
- Rule: When a recipe requirement lacks the evidence needed to evaluate a
  requested constraint, the recipe must be dropped from the eligible pool. Missing
  or unstated evidence must never be treated as a passing or compliant value, and
  the drop cause must be reported as evidence-absent, distinct from present-
  evidence-rules-out.
- Why: Proposal Explainability Stance; Behavioral Rules Conservative Allergen,
  No Inferred Dietary Compliance, Missing Nutrition Profile.
- Check: Named test fixture — `tests/features/dietary/test_domain_rules.py`
  asserts that an `unknown` / blank / undeclared state yields a drop with an
  evidence-absent cause, and that no code path maps absent evidence to
  pass/compliant/zero.

### R-6 Severe allergen drops; mild allergen warns
- Rule: A declared severe allergen must drop the recipe. A declared mild allergen
  must retain the recipe with a user-visible warning on the offending ingredient.
  Undeclared or unknown allergen evidence must drop the recipe as evidence-absent.
- Why: Q4, Q5; Behavioral Rule Conservative Allergen Policy.
- Check: Named test fixture — `tests/features/dietary/test_domain_rules.py`
  covers severe → drop, mild → retain-with-warning, undeclared → drop, and asserts
  the warning attaches to the specific offending ingredient.

### R-7 No inferred dietary compliance
- Rule: For halal, vegan, and vegetarian requirements, only explicit compliance
  retains the recipe. Any unknown, blank, or undeclared state must drop the recipe
  as evidence-absent.
- Why: Q6; Behavioral Rule No Inferred Dietary Compliance.
- Check: Named test fixture — `tests/features/dietary/test_domain_rules.py`
  asserts `unknown` status produces a drop and that only an explicit compliant
  value retains.

### R-8 Stale price offers are unavailable
- Rule: A retail price offer past its freshness threshold must be treated as
  unavailable and must never be used, with or without a flag. If no fresh offer
  exists for a requirement, the recipe must be dropped as evidence-absent. The
  threshold value is set in the spec, not here.
- Why: Q3; Behavioral Rule Price Snapshot Staleness; known temporal degradation of
  retail data.
- Check: Named test fixture — `tests/features/calculator/test_domain_cost.py`
  parameterized over the spec threshold asserts an offer past the threshold is
  excluded and that no fresh offer drops the recipe with an evidence-absent cause.

### R-9 Nutrient constraints require a profile
- Rule: A candidate with no nutrition profile must not satisfy any nutrient
  constraint it would serve and must not be treated as zero. If no candidate for a
  requirement has a profile, the nutrient constraint cannot be evaluated and the
  recipe must be dropped as evidence-absent.
- Why: Behavioral Rule Missing Nutrition Profile.
- Check: Named test fixture —
  `tests/features/calculator/test_domain_nutrition.py` asserts a profile-less
  candidate contributes no value (not zero) and that a requirement with no
  profiled candidate drops with an evidence-absent cause.

### R-10 Compatible unit basis required for cost
- Rule: Consumed-ingredient cost must be computed only when package size and
  recipe quantity share a compatible unit basis. A product with an incompatible
  basis must not be used for cost; if no compatible product remains for a
  requirement, the recipe must be dropped as evidence-absent.
- Why: Q2; Behavioral Rule Compatible Unit Basis Required.
- Check: Named test fixture —
  `tests/features/calculator/test_domain_conversion.py` asserts incompatible-basis
  products are excluded from cost and that a requirement left with no compatible
  product drops with an evidence-absent cause.

## Cost & nutrition correctness

### R-11 Consumed cost is distinct from retail package price
- Rule: Cost output must report the consumed-ingredient cost separately from the
  whole-package retail purchase price; the two values must never be conflated into
  a single figure.
- Why: Proposal G-3; API structure.
- Check: Named test fixture — `tests/features/calculator/test_domain_cost.py`
  asserts both values are exposed as separate fields with distinct values for a
  sub-package quantity.

### R-12 Deterministic nutrient conflict precedence
- Rule: When nutrient values from different sources disagree, the system must
  apply a single deterministic precedence rule that is stable across runs and
  produces the same winner for the same inputs. The specific precedence order is
  defined in the spec.
- Why: Q7; Behavioral Rule Nutrient Conflict Precedence; G-7 (reproducibility).
- Check: Named test fixture —
  `tests/features/calculator/test_domain_nutrition.py` runs each precedence case
  twice and asserts identical outcomes, and asserts the implemented order matches
  the order declared in the spec.

### R-13 Selection by best score, no confidence floor
- Rule: A requirement must be unmappable only when its candidate set is empty.
  There must be no minimum confidence threshold; among existing candidates,
  selection must be by best score, and confidence (closed interval [0, 1]) must be
  recorded in the execution trace.
- Why: Q1; Behavioral Rule Mapping Acceptance Floor.
- Check: Named test fixture —
  `tests/features/calculator/test_mapping_selection.py` constructs a candidate set
  with one very-low-confidence candidate and asserts it is selected when it is the
  only one; asserts ranking by score with multiple candidates; asserts the chosen
  candidate's confidence appears in the trace.

### R-14 Feasibility floor names the binding constraint
- Rule: If, after filtering and all permitted relaxations, no set of retained
  recipes satisfies `horizon_days × meals_per_day`, the plan must not be produced
  and the response must name the binding constraint(s). A plan must never be
  returned as unfeasible while a producible plan exists.
- Why: Proposal G-1; Behavioral Rule Plan Feasibility Floor.
- Check: Named test fixture — `tests/features/plans/test_domain_solver.py`
  asserts (a) an infeasible request returns no plan with named binding
  constraint(s), and (b) a satisfiable request returns a plan rather than an
  unfeasible result.

## Data reproducibility & provenance

### R-15 Data is reproducible and quality-gated
- Rule: The data underlying recommendations must be reproducible from source
  snapshots and must pass quality gates on entity counts and referential integrity
  before it is queryable as a graph.
- Why: Proposal G-7; system design ingestion flow.
- Check: CI command — the data-preparation quality-gate job asserts expected
  entity counts and zero dangling `REQUIRES` / `FULFILLS` references before load
  is accepted.

## Explainability

### R-16 User response excludes audit-only provenance
- Rule: The user-facing response must expose only the resolved food concept,
  chosen offer, per-requirement constraint outcome, and warned conditions.
  Mapping confidence, normalization version, and source IDs must not be returned
  to the user and must be retained only in the execution trace.
- Why: Q8 (scopes G-6).
- Check: Named test fixture — `tests/api/test_response_schema.py` serializes a
  representative response and asserts the allowed key set, failing if
  `confidence`, `normalization_version`, or any `source_*` / `*_id` provenance
  field appears in the user-facing payload. A companion assertion confirms those
  fields are present in the trace object.

### R-17 Three-level explanations with distinct drop causes
- Rule: Every recommendation must expose explanations at plan, recipe, and
  constraint granularity, including dropped candidates. A drop caused by
  evidence-absent must be reported distinctly from a drop caused by present
  evidence that rules the recipe out.
- Why: Proposal G-2, G-6; Explainability Stance.
- Check: Named test fixture — `tests/api/test_explanation_shape.py` builds two
  responses, one where a recipe is dropped for absent evidence and one where it
  is dropped for present-but-excluding evidence, and asserts each carries the
  distinct cause code and that all three levels of outcome are present in both.

## Amendment process

Changes to this file are made only through `amendments/A-*.md`. An amendment must
cite its trigger, be marked `approved`, and increment `Version`. Rules are
numbered R-1..R-N monotonically; renumbering is a breaking change and requires an
amendment. This file carries no changelog — `amendments/` is the changelog.

<!-- Number rules R-1..R-N monotonically across all categories. Downstream
     artifacts cite rule IDs; renumbering is a breaking change and requires an
     amendment. Aim for 8–15 rules. More than 20 means you are writing a spec. -->
