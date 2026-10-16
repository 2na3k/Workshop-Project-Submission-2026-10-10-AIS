---
feature: p3-001-workflow-recommendation-service
---

# Spec - Workflow recommendation service

## Summary

This feature builds the recommendation **workflow** for Remy: a LangGraph
orchestration that turns a user's meal-planning request into a recommendation
outcome plus a workflow-level trace. It is greenfield — no workflow, response
contract, chat, or web surface exists yet. The feature owns the five conceptual
stages drawn in `workflow_diagram.md`: **Extract Constraints**, **Find Recipe
Candidates**, **Resolve Food Candidates**, **Filter & Rank**, and **Generate
Response**.

Those five stages are realized as **three workflow nodes**: *Extract
Constraints*, *Plan*, and *Generate Response*. The Plan node delegates the
middle three stages (Find Recipe Candidates, Resolve Food Candidates, Filter &
Rank) to the p2-003 plan path as a single call. The Neo4j interactions drawn in
the diagram belong to p2-003's internals; the workflow does not access the graph
itself. The plan-level trace (`PlanTrace`) records outcomes, not per-stage
steps, so the workflow records the Plan node as one step and does not observe or
reorder the plan's internal stages. (See Clarifications C-3.)

The workflow receives a user request, derives an explicit constraint set from
it (nutrition ranges, allergens, dietary flags, planning horizon), invokes the
p2-003 plan path (`PlanService.generate`) to produce a feasible plan (or a
named-binding-constraint infeasibility result), and returns both the
recommendation outcome and a workflow-level trace. The constitution's
reasoning-safety guarantees are established upstream in p2 and are **not**
re-decided here: the workflow does not re-filter, re-rank, re-solve, or soften
any drop cause that p2 produced. It orchestrates those stages and carries their
outcomes through to its caller without weakening them.

Two nodes use a language model: **Extract Constraints** parses the natural-
language request into the explicit constraint set the plan path consumes, and
**Generate Response** assembles a human-readable recommendation from the
deterministic plan result. The LLM is model-agnostic and defaults to a locally
hosted model. The LLM never decides eligibility, feasibility, drop cause,
allergen severity, tolerance, or constraint outcome — those come only from the
user's explicit statements and the deterministic p2 stages.

The workflow is the orchestration layer the conversational surface (p3-004,
`POST /chat`) and the web surface (p3-003) wrap. This feature does **not** own
those surfaces, the user-facing response contract (p3-002), cost/budget
evaluation, or streaming. It owns the workflow and the boundary of the trace it
produces.

**The workflow consumes whatever the plan produces.** Phase p2 closed with
data-coverage findings (DQ-1..DQ-7) tracked; the plan's candidate pool is
limited by the deployed graph's coverage. That quality is upstream of this
feature; the workflow neither compensates for nor masks it.

**Provenance reach (pass-through).** The workflow embeds `PlanTrace` unchanged
and passes through whatever `PlanTrace` carries; it neither fabricates nor
recovers fields `PlanTrace` does not carry. `PlanTrace`'s `RecipeOutcome` and
`RequirementOutcome` currently do not carry mapping confidence, normalization
version, or source identifiers, so R-16's trace-side retention clause and
R-13's "confidence recorded in the trace" are not satisfiable through p3-001.
This is recorded as **Finding F-P3-1** (see `## Tracked findings`), owned by
p2-003, with consequences for G-6 and p3-002.

## Traces to

- **G-2** — "Explainable recommendations." The workflow produces a
  recommendation outcome accompanied by an execution trace that carries the
  plan / recipe / constraint reasoning p2 established, so the recommendation
  can be explained rather than asserted.
- **G-6** — "Transparent, auditable reasoning." The workflow-level trace
  defines the boundary from which the downstream explanation contract (p3-002)
  draws, keeping audit-only provenance out of the user payload. **G-6's
  auditability is limited by Finding F-P3-1** — the trace carries whatever
  `PlanTrace` carries, and `PlanTrace` currently does not carry the provenance
  fields R-16 requires.
- **Roadmap phase p3 → p3-001-workflow-recommendation-service** *(new)* — "A
  LangGraph-based workflow that orchestrates recommendation generation:
  receives a user request, invokes the plan solver (p2-003), attaches the
  reasoning trace, and returns the recommendation result plus a workflow-level
  trace. The workflow defines the trace boundary that p3-002 consumes for
  explanation assembly."
- **Phase p3 outcome** — "The backend recommendation surface is built
  end-to-end: a LangGraph workflow orchestrates constraint extraction, plan
  generation (via p2-003), and explanation assembly."
- **Roadmap shared contract** — "Recommendation execution result and trace
  boundary," shared with p3-002-explainable-response-contract,
  p3-003-web-planner-experience, and p3-004-conversational-constraint-interface.
- **Constitutional rules** (constitution v1.6):
  - **R-2** (inward dependency direction; `workflows` must not depend on
    `api`) — the workflow reaches the plan path only through a
    **workflow-owned interface** and never imports `api`. An adapter outside
    both packages (in `app`, the composition root) implements that interface by
    calling `PlanService.generate`. (Clarification C-1.)
  - **R-3** (stack shape fixed unless amended) — LangGraph and LangChain are
    **libraries within the existing Python backend shape**; they introduce no
    non-Python backend, row-store data layer, relational serving layer, or
    heuristic solver. The solver and graph store are unchanged. R-3 does not
    name LangGraph itself; this is a same-shape addition, and the constitution
    owner has confirmed that LangGraph/LangChain and a locally hosted LLM
    runtime fit under R-3 without an amendment. (Clarification C-5.)
  - **R-5** (absent evidence drops, never includes) — the workflow carries
    p2's evidence-absent drops through unchanged; no workflow node, and in
    particular no LLM node, may convert an absent-evidence drop into an
    inclusion or a passing value.
  - **R-6** (severe allergen drops; mild allergen warns) — the workflow carries
    p2's ingredient-scoped mild-allergen warnings through to the outcome and the
    generated text, and never lowers an allergen's severity during extraction.
  - **R-14** (feasibility floor names the binding constraint; as amended by
    **A-005**) — the workflow carries the infeasibility result, binding
    constraints, relaxed label, and applied tolerance unchanged. Only
    nutrient-bound widening is a permitted relaxation, with
    `nutrient_tolerance_pct` in `[0, 25]`, default `0`; the workflow never
    applies or widens any relaxation itself.
  - **R-16** (user response excludes audit-only provenance) — the workflow
    excludes `confidence`, `normalization_version`, and `source_*`/`*_id`
    fields from the user-displayable portion. **Trace-side retention is
    currently not satisfiable through p3-001:** `PlanTrace` does not carry
    those fields, contradicting p2-003's spec text and R-16's trace-side check.
    This is Finding F-P3-1, owned by p2-003; the workflow passes through
    whatever `PlanTrace` carries and neither fabricates nor recovers the
    missing fields. The workflow does **not** extend R-16's exclusion list —
    restricting prices, `listing_key`, or `price_ref` from the user payload is
    p3-002's decision.
  - **R-17** (three-level explanations with distinct drop causes) — the
    workflow preserves the plan / recipe / constraint reasoning, including
    dropped candidates, and the distinct `evidence-absent` /
    `present-evidence-excludes` / `unmapped` drop causes p2 produced, for
    feasible **and** infeasible outcomes.
- **Amendments:** **A-005** (R-14 relaxation set) and **A-006** (R-8/R-10:
  cost/budget out of p2; recipe-level cost drop owned by p3-004) are approved
  and merged into constitution v1.6.

## User-facing behavior

> "User-facing" here means the behavior observable by the workflow's **caller**
> (the chat and web surfaces, p3-004 / p3-003). This feature does not render
> text to an end user; p3-002 and p3-004 own that. The workflow's observable
> contract is its input, its outcome, and its trace.

- Given a meal-planning request, the workflow runs three nodes in order —
  Extract Constraints → Plan → Generate Response — and returns a single
  **outcome** plus a **workflow-level trace**. The trace records the Plan node
  as one step; the plan's three-level reasoning comes from the embedded
  `PlanTrace`.
- The **outcome** is exactly one of: a **plan** result, an **infeasible**
  result, or a **failure** (naming the failing node and reason). Every outcome,
  including failures, is paired with a trace.
- The **Extract Constraints** node converts the incoming request into the
  explicit constraint set the plan path consumes (planning horizon, servings,
  nutrient targets/limits, allergen declarations and severities, dietary flags,
  and the nutrient-tolerance setting). When the request is natural language, the
  LLM performs the extraction; when the request already carries a structured
  constraint set, extraction is a pass-through.
- Extraction is **faithful, not inventive**: every allergen or dietary
  constraint the user states appears in the constraint set; allergen severity
  is set only on an explicit user statement (otherwise the plan path's
  conservative default applies) and is never downgraded; `nutrient_tolerance_pct`
  is non-zero only on an explicit user request; and anything the user states
  that the contract cannot express (for example a cost or budget limit,
  ingredient dislikes, cuisine preference) is reported as **unapplied** rather
  than silently omitted.
- The **Plan node** delegates to the p2-003 plan path through a workflow-owned
  interface. The workflow does not re-implement filtering, resolution, ranking,
  or solving.
- When the plan path returns a feasible plan, the outcome carries the selected
  recipes per slot and the plan's three-level reasoning (plan / recipe /
  constraint outcomes, including dropped candidates) unchanged, and carries any
  mild-allergen ingredient warnings.
- When the plan path returns an infeasibility result, the outcome carries that
  result with the named binding constraint(s) and the three-level reasoning
  intact. The workflow does not fabricate a plan, retry with silently loosened
  constraints, or present an infeasible request as a degraded success.
- When the plan path produces a plan under a permitted nutrient-tolerance
  relaxation, the workflow carries the relaxed label and the applied tolerance
  through unchanged.
- The **Generate Response** node produces a human-readable recommendation from
  the deterministic plan result using the LLM. The text re-expresses the
  deterministic outcomes; it does not introduce recipes, change selections,
  invent constraint outcomes, drop a mild-allergen warning, or restate an
  evidence-absent drop as permissive or passing. The workflow verifies this
  deterministically before returning (AC-11).
- Every outcome is accompanied by a workflow-level trace that records which
  nodes ran, the raw extraction output, the constraint set, unapplied
  constraints, model and provider identity, node outcomes, and the embedded
  `PlanTrace`. The user-displayable portion carries no audit-only provenance
  (R-16). The workflow does not fabricate or recover provenance that
  `PlanTrace` does not carry; where R-16's trace-side retention is unmet, it is
  Finding F-P3-1, owned by p2-003.
- When a node fails (the LLM is unavailable, times out, or returns
  out-of-contract output; the plan path is unavailable; the request cannot be
  parsed into a constraint set; the constraint set is contradictory; or the
  generated text fails verification), the workflow returns an explicit failure
  for that node. It does not return a partial recommendation presented as
  complete, and no trace claims a successful recommendation.
- **Failure is all-or-nothing.** If the plan path succeeded or proved
  infeasibility but Generate Response fails, the outcome is a failure; the
  deterministic result is retained in the trace but is not presented as the
  recommendation. (Clarification C-4.)

## Acceptance criteria

- **AC-1** Given a meal-planning request, when the workflow runs, then it
  executes the nodes Extract Constraints → Plan → Generate Response in that
  order and returns exactly one outcome paired with exactly one workflow-level
  trace. When a node fails, later nodes do not run, and the trace records which
  nodes ran. The trace records the Plan node as a single step; the plan's
  internal stages are not separately recorded.

- **AC-2** Given a natural-language request, when Extract Constraints runs,
  then it produces an explicit constraint set (planning horizon, servings,
  nutrient targets/limits, allergen declarations and severities, dietary flags,
  and the nutrient-tolerance setting) that is passed to the plan path, and the
  raw extraction output and resulting constraint set are recorded in the trace.

- **AC-3** Given a request that carries a structured constraint set, when
  Extract Constraints runs, then the constraint set is used without alteration
  and no LLM extraction is required. A request is structured if and only if it
  carries a constraint set; if it also carries free text, the set is still used
  unaltered and constraints appearing only in the free text are reported as
  unapplied (AC-17).

- **AC-4** Given an extracted constraint set, when the Plan node runs, then the
  workflow invokes `PlanService.generate` only through the workflow-owned plan
  interface, does not re-implement candidate filtering, food-concept
  resolution, ranking, or solving, and `uv run lint-imports` passes including
  the contract "workflows does not depend on api". (R-2, R-3.)

- **AC-5** Given a request for which the plan path returns a feasible plan,
  when the workflow completes, then the plan outcome carries the selected
  recipes for every `(day, meal)` slot of the horizon and the plan's
  three-level reasoning (plan / recipe / constraint outcomes, including dropped
  candidates) unchanged from the plan path's output.

- **AC-6** Given a request for which the plan path returns an infeasibility
  result with named binding constraint(s), when the workflow completes, then the
  infeasible outcome carries the binding constraint(s) and the three-level
  reasoning, including dropped-candidate explanations, intact, and no
  fabricated or degraded plan is returned. (R-14, R-17.)

- **AC-7** Given a plan produced under a permitted nutrient-tolerance
  relaxation, when the workflow completes, then the outcome carries the relaxed
  label and the applied tolerance value unchanged. (R-14, A-005.)

- **AC-8** Given a plan result in which a recipe was dropped by p2 with an
  `evidence-absent` cause, when Generate Response produces the text, then the
  text does not restate that drop as a passing, compliant, or permissive
  outcome, and the `evidence-absent` cause remains distinct from
  `present-evidence-excludes` and `unmapped` in the outcome. (R-5, R-17.)

- **AC-9** Given any outcome produced by the workflow, when the
  user-displayable portion is examined, then it carries no `confidence`, no
  `normalization_version`, and no `source_*`/`*_id` provenance field. This list
  is R-16's; the workflow does not extend it. The input given to Generate
  Response also excludes R-16's provenance fields, so they cannot appear in
  generated text. The workflow trace is never part of the user-displayable
  portion. (R-16.)

- **AC-10** Given any outcome, when the trace is examined, then it records the
  workflow-level facts (nodes run, raw extraction output, parsed constraint
  set, unapplied constraints, model and provider identity, workflow outcome,
  node outcomes, and the failure node/reason when the outcome is `failure`) and
  embeds the `PlanTrace` unchanged. Through the embedded `PlanTrace`, the three
  levels of outcome (plan / recipe / constraint), the drop causes and their
  precedence, the binding constraints, the applied tolerance, and the resolved
  concept and selected offer per requirement are reachable. The workflow
  passes through whatever `PlanTrace` carries, unchanged; it neither fabricates
  nor recovers fields `PlanTrace` does not carry. R-13's "confidence recorded
  in the trace" and R-16's trace-side retention are asserted at the p2 layer
  (see Finding F-P3-1).

- **AC-11** Given the Generate Response node, when it produces text, then a
  deterministic check on the node's structured output (the LLM's referenced
  recipe IDs, requirement IDs, and drop causes, which the node produces
  alongside the text) verifies that every referenced recipe and constraint
  outcome is a subset of those in the plan result, that drop-cause wording maps
  to the plan's recorded causes, and that no evidence-absent drop is expressed
  as permissive. The check is on the structured side of the node's output, not
  on parsing the text. If the check fails, the workflow returns a `failure`
  outcome for the Generate Response node and the trace records the check
  failure. (R-5.)

- **AC-12** Given the LLM is unavailable, exceeds its time budget, or returns
  out-of-contract output after the permitted bounded re-prompts, during
  Extract Constraints or Generate Response, when the workflow runs, then it
  returns a `failure` outcome naming the node; it returns no recommendation and
  no trace claims a successful recommendation.

- **AC-13** Given the plan path is unavailable at runtime, when the workflow
  runs, then it returns a `failure` outcome for the Plan node; it does not
  fabricate a plan and no trace claims feasibility.

- **AC-14** Given a request that cannot be parsed into a constraint set, that
  lacks a planning horizon, or whose constraints the workflow's constraint
  model determines to be invalid, when Extract Constraints runs, then the
  workflow returns a `failure` outcome before the plan path is invoked, and the
  failure is recorded in the trace. The workflow's constraint model validates:
  the presence of `horizon_days` and `meals_per_day`; the closed interval
  `[0, 25]` for `nutrient_tolerance_pct`; that nutrient codes are drawn from the
  plan path's known set; and that `min`/`max` bounds are well-formed (both
  numeric, `min <= max` when both are present). Cross-field business validation
  the plan path performs beyond this set (for example, a request whose only
  constraint is unreachable given the graph) remains the plan path's
  responsibility and is surfaced through the interface as a failure rather than
  coerced. No offending field is silently dropped or coerced.

- **AC-15** Given the plan path returns an empty eligible pool (no recipe
  survived filtering/dropping), when the workflow completes, then the
  infeasible outcome identifies that no recipe survived, distinct from the case
  where recipes survived but no assignment satisfied the horizon, with the
  three-level reasoning including dropped candidates.

- **AC-16** Given a representative plan result (feasible, infeasible, empty
  pool, relaxed, multi-cause drops, mild-allergen warnings), when it passes
  through the adapter between `PlanService.generate` and the workflow-owned
  interface, then the feasibility outcome and reason, binding constraints,
  applied tolerance, recipe outcomes, requirement outcomes, the three drop
  causes and their precedence, and ingredient warnings survive unchanged
  (contract test).

- **AC-17** Given a natural-language request stating an allergen or dietary
  requirement, when Extract Constraints runs, then every stated allergen and
  dietary flag appears in the constraint set. Given a request stating something
  the contract cannot express (cost/budget, dislikes, cuisine), then it is
  listed as unapplied in both the outcome and the trace, never silently
  omitted.

- **AC-18** Given a natural-language request, when Extract Constraints runs,
  then allergen severity is set only when the user explicitly states it (an
  ambiguous phrase such as "a bit allergic" does not produce `mild`; the plan
  path's conservative default applies) and is never downgraded, and
  `nutrient_tolerance_pct` is 0 unless the user explicitly requests relaxation.

- **AC-19** Given a plan result containing a mild-allergen ingredient warning,
  when the workflow completes, then the warning, scoped to the offending
  ingredient, is present in the outcome, and the generated text includes it.
  (R-6.)

- **AC-20** Given a request with only a horizon and no other constraints, when
  the workflow runs, then extraction yields an empty constraint set and the
  plan path decides feasibility on horizon coverage alone.

- **AC-21** Given conformance evidence for this feature, then:
  - Workflow output passes the **workflow-side equivalent** of R-16's
    user-payload assertion: the user-displayable portion carries no
    `confidence`, no `normalization_version`, and no `source_*` / `*_id`
    field. The workflow test imports the same exclusion list as the
    calculator's `tests/features/calculator/test_response_schema.py`
    (which is R-16's actual location — the constitution names
    `tests/api/test_response_schema.py`; the divergence is p2-002's F-D,
    tracked for phase review).
  - Workflow output passes the **workflow-side equivalent** of R-17's
    contract: the three levels of outcome are present, and `evidence-absent`
    drops are distinct from `present-evidence-excludes` and `unmapped`.
    The constitution names `tests/api/test_explanation_shape.py`, which does
    not exist; R-17's named fixture is absent and its owner is assigned at
    phase review (likely p3-002).
  - All workflow tests run with a fake LLM and a fake plan interface; no
    test requires a live model.
  - **The trace-side portion of R-16's check is not satisfiable by p3-001** —
    `PlanTrace` does not carry the provenance fields. Recorded as Finding
    F-P3-1, owned by p2-003. The trace-side assertion is `xfail` with a
    reason referencing F-P3-1.

## Edge cases & errors

- **Empty eligible pool.** Surfaced as an infeasible outcome with its named
  cause intact; no retry with loosened constraints (AC-15).
- **Infeasible under tolerance.** The plan path reports hard infeasibility even
  under the permitted widening. The workflow returns the named binding
  constraint(s); it does not widen further or degrade the plan (AC-6).
- **LLM returns malformed or out-of-contract extraction.** The workflow may
  re-prompt a bounded number of times (the limit is a plan-stage decision). If
  the result still fails the workflow's constraint model or the plan path's
  validation, it returns an explicit failure before solving or from the plan
  interface; it does not coerce the offending field into a passing value
  (AC-12, AC-14).
- **LLM hallucination at response generation.** Caught by the deterministic
  check on the node's structured output (AC-11); failure is explicit.
- **Plan path / solver unavailable.** Explicit failure; no degraded fallback
  (AC-13).
- **LLM timeout.** Treated as LLM-unavailable for the affected node. The time
  budget is configurable and set at plan stage (AC-12).
- **Request with no constraints.** Valid (AC-20).
- **Missing horizon in a natural-language request.** Explicit extraction
  failure; the workflow does not invent a default horizon (AC-14).
- **Mixed structured and free-text request.** Structured set wins; free-text-only
  constraints are reported as unapplied (AC-3).
- **Partial-coverage data (DQ-1..DQ-7).** The plan's candidate pool may be a
  small, biased slice of the recipe graph. The workflow does not compensate
  for coverage gaps; the recommendation reflects the plan's output.
- **Multi-cause drops.** The workflow preserves p2's precedence and keeps all
  applicable causes distinguishable (R-17, AC-16).
- **Generate Response fails after a successful plan.** All-or-nothing: the
  outcome is a failure; the deterministic result stays in the trace only (C-4).
- **Provenance `PlanTrace` does not carry.** Not available through the workflow
  trace; the workflow does not fabricate or recompute it. See Finding F-P3-1.

## Tracked findings

### Finding F-P3-1 — `PlanTrace` does not carry R-16's provenance fields

- **Trigger:** Verifying the trace boundary against R-16's trace-side check
  (`tests/api/test_response_schema.py`) and R-13's "confidence recorded in the
  trace" requirement showed that `PlanTrace`'s `RecipeOutcome` and
  `RequirementOutcome` carry no mapping confidence, normalization version, or
  source identifiers. p2-003's spec text asserts the plan-level trace carries
  audit provenance; the implementation does not.
- **Consequence:**
  - G-6's auditability is limited to what `PlanTrace` carries.
  - R-16's trace-side check fails on the trace object.
  - p3-002's explanation contract cannot rely on the p3-001 trace carrying the
    provenance; it can reach plan / recipe / constraint outcomes and drop
    causes, but not audit-only provenance.
- **Owner:** p2-003 (the layer whose spec asserted the retention).
- **Resolution path:** Either p2-003 amends its plan-level trace (adding the
  R-16 provenance fields to `RecipeOutcome` and `RequirementOutcome`), or the
  p2-003 spec is amended to drop the claim and R-16's trace-side check is
  scoped to `CalculationTrace`. Either resolution routes through p2-003's spec
  owner.
- **Posture:** p3-001 proceeds with the finding tracked. The trace boundary
  asserts pass-through of whatever `PlanTrace` carries; it does not require the
  missing fields and does not fabricate them. AC-21's trace-side assertion is
  expected to fail until F-P3-1 resolves.

## Non-goals

- **Frontend / web planner UI (p3-003).**
- **Cost and budget evaluation on the initial turn.** Owned by p3-004 (per
  A-006); the workflow does not evaluate cost or budget and does not consume
  `MISSING_PACKAGE_DATA` as a recipe-level drop. A cost/budget statement in a
  request is reported as unapplied (AC-17).
- **The user-facing response contract (p3-002).** This feature produces the
  trace boundary p3-002 consumes, not the response contract itself. Whether the
  user payload restricts prices, `listing_key`, or `price_ref` is p3-002's
  decision, not this feature's.
- **The conversational surface (p3-004) and `POST /chat`.** HTTP/SSE wrapper,
  turn management, and cross-turn constraint extraction are p3-004's.
- **Streaming.** The workflow returns one completed outcome; any streaming
  layer is p3-004's.
- **The deprioritised and deferred endpoints.** `/verify-dietary` and
  `/recipes/{id}` (deprioritised), `/recommendations/cold-start` (deferred).
- **Re-deciding p2's reasoning.** Filtering, resolution, ranking, feasibility
  solving, and drop-cause determination stay in p2.
- **Recovering provenance p2 does not expose.** The workflow does not call the
  calculator, or change `PlanTrace`, to obtain `CalculationTrace` data. Doing so
  would reopen p2-003 and is a follow-up (Finding F-P3-1), not part of this
  feature.
- **Importing `api` internals or extracting a shared contract package.** The
  latter would reopen the closed p2-003 feature.
- **Changing the solver, graph, or data layer shape (R-3).**
- **Fixing the data-coverage findings (DQ-1..DQ-7) or Finding F-P3-1.**
- **Choosing the trace's internal data structures, module layout, file names,
  LLM client library, or configuration variable names.** Plan-stage decisions.
- **Runtime LLM provider failover.** The provider is chosen by configuration;
  the workflow does not silently fall back from a local model to a hosted
  provider, because requests may contain dietary and allergen information.

## Interfaces & dependencies

### Endpoint-to-feature mapping

| Surface / endpoint | Owner | In scope for p3-001? |
|---|---|---|
| The LangGraph recommendation workflow (three nodes, five conceptual stages) | **p3-001** | **Yes** — this feature |
| `POST /chat` (conversational wrapper around the workflow) | p3-004 | No — wraps the workflow |
| Web request/response surface for the planner UI | p3-003 | No — separate frontend effort |
| User-facing three-level explanation response contract | p3-002 | No — consumes p3-001's trace boundary |
| `/verify-dietary`, `/recipes/{id}` | — | No — deprioritised |
| `/recommendations/cold-start` | — | No — deferred |

### Input contract

- The workflow receives a user meal-planning request, either natural language or
  carrying a structured constraint set. Extract Constraints produces the
  explicit constraint set the plan path consumes: planning horizon
  (`horizon_days`, `meals_per_day`), `servings`, nutrient targets/limits,
  allergen declarations with severity, dietary flags, and the nutrient-tolerance
  setting (`nutrient_tolerance_pct`, closed interval `[0, 25]`, default `0`).
- The workflow validates the constraint set against **its own constraint
  model** (AC-14 names what it validates) and fails early on what it can detect.
  The plan path's request validation remains the authority for cross-field
  business validation; its rejections are surfaced as validation failures
  through the interface rather than coerced.

### Output contract

- The workflow returns an **outcome** plus a **workflow-level trace**. The
  outcome is a discriminated result: `plan`, `infeasible`, or
  `failure(node, reason)`.
  - `plan` and `infeasible` carry the plan path's feasibility result, the
    three-level reasoning (including dropped candidates) unchanged, the relaxed
    label and applied tolerance when applicable, mild-allergen ingredient
    warnings, the list of unapplied constraints, and the human-readable
    recommendation from Generate Response.
  - The user-displayable portion of the outcome excludes R-16's provenance
    fields.
- The precise field layout is **not** fixed here; the user-facing response
  contract is p3-002's.

### Trace boundary

- The workflow-level trace is a **self-contained, versioned envelope**. It
  carries:
  - a schema version identifying the envelope's shape;
  - the workflow outcome (which of `plan`, `infeasible`, or `failure`) with the
    failing node and reason when applicable;
  - the workflow input: the raw user message, the parsed constraint set, and
    the list of unapplied constraints with reasons;
  - one entry per node that ran, with the node name and its outcome (the Plan
    node is one entry; the plan's internal stages are not separately recorded);
  - one entry per LLM invocation, with the node, provider, model, prompt, raw
    response, parsed response, and duration;
  - the embedded `PlanTrace` unchanged, as a nested sub-object.
- The envelope carries a required schema version so p3-002 can detect shape
  changes.
- `PlanTrace` is a plain dataclass; serialization is an explicit workflow
  responsibility.
- The trace holds audit provenance and is never part of the user-displayable
  payload (R-16), to the extent it carries that provenance.
- **Reach invariant.** Through the embedded `PlanTrace`, p3-002 can reach plan
  / recipe / constraint outcomes, drop causes and precedence, binding
  constraints, applied tolerance, and the resolved concept and selected offer
  per requirement. `PlanTrace` does not currently carry mapping confidence,
  normalization version, or source identifiers; their absence is Finding
  F-P3-1 (see `## Tracked findings`), owned by p2-003, not a p3-001 limitation.
  The workflow does not fabricate or recover them.
- The exact field names and the envelope's dataclass shapes are plan-stage
  decisions.

### Dependency on p2-003 (the plan path)

- The workflow reaches the plan path only through a **workflow-owned plan
  interface** (a port) defined in the workflow's own typed models. The workflow
  never imports `api`.
- An **adapter in `app`**, the composition root, implements that interface by
  calling `PlanService.generate`. The interface's return shape is
  `(PlanResponse, PlanTrace)`, matching `CostNutritionService.calculate`'s
  `(CostNutritionResponse, CalculationTrace)` pattern. `generate_v2` is not
  used. (Clarifications C-1 and C-7; p2-003 reopen per Q4.)
- The adapter is the **only** place that maps between workflow models and
  `PlanRequest` / `PlanResponse` / `PlanTrace`, and it must lose nothing
  (AC-16).
- Verified entry points: `SystemCode/remy/api/src/api/features/plan/service.py`
  and `router.py`.
- The `.importlinter` contracts do not forbid `app → api` or `app → workflows`.
  `app` is not currently a root package, so the contracts do not analyze it; the
  plan stage adds it (Open question Q2).

### LLM dependency

- The workflow uses a language model in exactly two nodes: **Extract
  Constraints** and **Generate Response**.
- The LLM is **model-agnostic**, defaulting to a **locally hosted model**, with
  hosted providers available by configuration. Provider selection is
  configuration, not runtime failover (see Non-goals). The model and provider
  identity are recorded in the trace.
- The LLM never decides eligibility, feasibility, ranking, drop cause, allergen
  severity, tolerance, or constraint outcome (AC-8, AC-11, AC-18).
- The Generate Response node produces **structured output alongside the text**
  (referenced recipe IDs, requirement IDs, and drop causes) so AC-11's
  deterministic check operates on structure, not on parsing natural language.

### Downstream dependencies

- **p3-002** consumes the workflow-level trace boundary.
- **p3-004** wraps the workflow in `POST /chat` and owns cost/budget on
  follow-up turns.
- **p3-003** (separate effort) consumes p3-002's response shape.

### Runtime / data dependency

- The plan path reads the canonical graph, which remains subject to the tracked
  `data-prep-price-path` finding and DQ-1..DQ-7. Conformance evidence uses
  approved fixtures per the phase posture.

## Open questions

None blocking. All resolved and recorded under `## Clarifications` as
C-1..C-7.

## Clarifications

- **C-1 (plan interface, 2026-10-15, spec review):** The workflow reaches the
  plan path through a workflow-owned interface (dependency inversion), with the
  adapter in `app` (composition root) calling `PlanService.generate`
  (`generate_v2` is not used). Rationale: satisfies R-2 without touching closed
  p2-003 code beyond the return-shape fix, avoids a network hop and duplicated
  request validation that HTTP would force, and keeps the workflow testable
  with a fake interface. A shared contract package was rejected because it
  reopens p2-003 more than necessary. `.importlinter` permits the placement
  (subject to Q2).
- **C-2 (trace, 2026-10-15, spec review):** The workflow trace embeds
  `PlanTrace` unchanged inside a versioned envelope. `PlanTrace` carries no link
  to `CalculationTrace` and no per-stage records, so only `PlanTrace` is
  embedded and the Plan node is recorded as one step. Rationale: no persisted
  trace store or trace IDs exist, so a reference would dangle; embedding keeps
  the trace self-contained for what `PlanTrace` carries. The structure is a
  plan-stage decision. Provenance that `CalculationTrace` carries is not
  reachable; this is Finding F-P3-1, owned by p2-003.
- **C-3 (diagram reconciliation, 2026-10-15, spec review):**
  `workflow_diagram.md` is conceptual. The workflow has three nodes (Extract
  Constraints, Plan, Generate Response); the diagram's Neo4j edges belong to
  p2-003's internals; the plan's internal stages are not separately observable
  because `PlanTrace` does not record them. Early-exit failure edges exist that
  the diagram does not draw.
- **C-4 (failure semantics, 2026-10-15, spec review):** Outcomes are
  `plan | infeasible | failure(node, reason)`, always paired with a trace.
  Failure is all-or-nothing: a Generate Response failure after a successful plan
  or proven infeasibility yields a failure outcome, with the deterministic
  result retained in the trace only.
- **C-5 (R-3, 2026-10-15, spec review):** LangGraph/LangChain and a locally
  hosted LLM runtime are same-shape additions under R-3 and need no amendment.
  Confirmed by the project owner.
- **C-6 (amendments, 2026-10-15, spec review):** A-005 and A-006 are approved
  and merged into constitution v1.6. AC-7 and the cost non-goal are no longer
  provisional.
- **C-7 (p2-003 return shape, 2026-10-15, spec review):** `PlanService.generate`
  currently returns `PlanResponse` and stores the trace on `self.last_trace`.
  p2-003 reopens to change `generate` to return `(PlanResponse, PlanTrace)`,
  matching `CostNutritionService.calculate`. The workflow-owned plan interface
  returns the tuple. This is a small, additive change to a closed feature and is
  the correct fix (the alternative — the adapter reading `last_trace` — is
  stateful and non-reentrant). The p2-003 reopen carries a follow-up finding in
  p2-003's decisions file.
- **C-8 (AC-21 conformance paths, 2026-10-16, spec review):** AC-21's named
  fixtures were corrected. R-16's assertion exists at
  `tests/features/calculator/test_response_schema.py` (the constitution names
  `tests/api/test_response_schema.py` — the divergence is p2-002's F-D).
  R-17's named fixture `tests/api/test_explanation_shape.py` does not exist;
  its owner is a phase-review decision. AC-21 now asserts the workflow-side
  equivalents and records both path findings. (Consequential — flag for
  decisions.md at close.)