---
feature: p3-004-conversational-constraint-interface
---

# Spec - Conversational constraint interface

## Summary

This feature **implements** the conversational recommendation surface the
earlier p3 features defined but did not build. Concretely, p3-004:

1. **Serves `POST /chat`** as a Server-Sent Events (SSE) endpoint that accepts a
   natural-language request, runs the p3-001 LangGraph workflow, and streams the
   p3-002 event vocabulary (`metadata`, `token`, `plan_updated`, `error`,
   `done`) back to the caller. The endpoint and its SSE transport live in
   `remy/app`, the only package permitted to import both `api` and `workflows`
   (R-2; p3-002 F-1).
2. **Extracts constraints from natural language** and detects a **cost/budget
   intent**, so that a request that asks about affordability ("under $5",
   "cheapest option", "what does this cost") is recognized and surfaces cost on
   the turn, while a request that does not mention cost does not.
3. **Re-expresses the deterministic explanation causes safely.** The workflow's
   Generate Response node (p3-001) is reused to turn the plan/recipe/constraint
   outcomes into user text without paraphrasing an `evidence-absent` drop into a
   permissive statement, and without inventing recipe IDs, requirement IDs, or
   drop causes the plan did not produce.
4. **Lands the recipe-level cost drop inherited from A-006.** When a requirement
   has no cost-eligible, fresh package (the calculator's `MISSING_PACKAGE_DATA`
   signal, per amended R-8/R-10), the recipe is dropped from the eligible pool
   with an `evidence-absent` cause, closing the R-8/R-10 recipe-level check
   obligation deferred from p2. This drop is enforced in the **api plan
   service** layer.

p3-004 **implements against** three frozen contracts and does not redefine them:
p3-002's request/event/explanation schemas (the *shape* of the surface),
p3-001's workflow nodes and `TraceEnvelope` (the *reasoning* the surface
delivers), and p2's reasoning and drop causes (the *outcomes* the surface
re-expresses). It is stateless per turn: each request is evaluated on its own
message and optional user context, with no server-side session memory.

**Phase p2 closed with the data-quality findings DQ-1..DQ-7 tracked, not
blocking.** p3-004 builds against whatever the plan produces; it does not
compensate for coverage gaps.

## Traces to

- **G-1 (budget aspect)** — "Feasible, budget-aware meal plans." p3-004 closes
  the R-8/R-10 recipe-level cost-drop obligation A-006 deferred from p2: a
  recipe whose requirement has no cost-eligible fresh package is dropped with an
  `evidence-absent` cause, and the conversational surface surfaces cost on a
  budget-intent turn.
- **G-2 (explainable recommendations)** — the conversational surface delivers
  the three-level explanation (plan / recipe / constraint) to the user and
  re-expresses the drop causes without softening them into permissive
  statements.
- **G-6 (transparent, auditable reasoning)** — every streamed response carries a
  stable `trace_id` referencing (never embedding) the execution trace; the user
  payload excludes R-16's audit-only provenance floor.
- **Roadmap phase p3 → p3-004-conversational-constraint-interface** *(new)* —
  "Conversational constraint extraction, turn-level recommendation delivery, and
  safe re-expression of deterministic explanation causes. **Additionally,
  p3-004 inherits the recipe-level cost drop from A-006**: when a requirement
  has no cost-eligible package (the calculator's `MISSING_PACKAGE_DATA` signal,
  per amended R-8/R-10), p3-004 drops the recipe from the eligible pool with an
  evidence-absent cause, asserting R-8's and R-10's recipe-level fixtures."
- **Phase p3 outcome** — "a conversational interface accepts natural-language
  requests, preserves the deterministic explanation causes, and surfaces cost on
  follow-up turns."
- **Phase p3 exit criteria** — "The conversational interface extracts
  constraints from natural language, delivers turn-level recommendations, and
  re-expresses explanation causes without paraphrasing them into permissive
  statements"; and "Cost and budget evaluation is in scope for p3-004 (per
  A-006); R-8's and R-10's recipe-level fixtures are satisfied by p3-004."
- **Roadmap shared contract** — "Conversational constraint extraction,
  turn-level recommendation delivery, safe re-expression of deterministic
  explanation causes, and the recipe-level cost drop inherited from R-8/R-10 per
  A-006," shared with p3-001, p3-002, and p3-003.
- **Constitutional rules** (constitution v1.7):
  - **R-8** (non-fresh price offers are unavailable) — p3-004 owns the
    recipe-level cost drop: a requirement left with no fresh package (the
    calculator's `MISSING_PACKAGE_DATA` signal) drops the recipe with an
    `evidence-absent` cause. p3-004 satisfies R-8's recipe-level fixture.
  - **R-10** (cost eligibility requires a convertible price basis) — p3-004 owns
    the recipe-level cost drop when no cost-eligible package exists for a
    requirement. p3-004 satisfies R-10's recipe-level fixture.
  - **R-16** (user response excludes audit-only provenance) — the `/chat` user
    payload exposes only the resolved food concept, chosen offer, per-requirement
    constraint outcome, and warned conditions; it excludes `confidence`,
    `normalization_version`, and any `source_*` / `*_id` provenance (R-16's
    floor), which is retained only in the trace.
  - **R-17** (three-level explanations with distinct drop causes) — the `/chat`
    surface exposes plan, recipe, and constraint granularity including dropped
    candidates, with `evidence-absent` reported distinctly from
    `present-evidence-excludes` and `unmapped`.
  - **R-2** (inward dependency direction) — the `/chat` endpoint lives in
    `remy/app`; the `.importlinter` contracts ("api does not depend on app")
    continue to pass.
  - **R-13** (selection by best score, confidence in trace) — p3-004 does not
    re-decide selection; it surfaces the plan's outcomes.
- **Amendments:**
  - **A-006** assigns p3-004 the recipe-level cost drop and the R-8/R-10
    recipe-level check obligation, enforced in the api plan service layer.
  - **A-007** fixes R-16's and R-17's named check paths to
    `SystemCode/remy/app/tests/api/<name>`; p3-004 asserts against those paths.

## User-facing behavior

- A caller sends a `POST /chat` request carrying a **session identifier**, a
  **message** (natural language), and an optional **user context** (for example,
  a current plan identifier). The request conforms to p3-002's `/chat` request
  schema; p3-004 serves it and does not redefine it.
- The server responds with a **stream of events** drawn only from p3-002's fixed
  vocabulary: `metadata`, `token`, `plan_updated`, `error`, `done`. p3-004 opens,
  frames, and closes the stream; it adds no new event type.
- p3-004 **extracts the request's constraints from natural language** (nutrient
  bounds, allergens, dietary flags, horizon/meals, tolerance) by running the
  p3-001 Extract Constraints node, and additionally **detects whether the turn
  expresses a cost or budget intent**. A message that references affordability,
  a price ceiling, or "what does it cost" carries a cost intent; a message with
  no cost reference does not.
- When the turn **carries a cost intent**, the response **surfaces cost** for
  the recipe and/or ingredient names in scope, computed on demand through the
  existing calculator service (consumed cost distinct from retail package cost,
  per R-11). A requirement with no cost-eligible fresh package surfaces the
  calculator's `MISSING_PACKAGE_DATA` condition rather than a fabricated price.
- When the turn **does not carry a cost intent**, cost is not computed or
  surfaced; the response is the plan/recipe/constraint explanation without cost
  figures.
- The **recommendation is exposed at three levels** — plan, recipe, constraint —
  with dropped candidates always explained. The user text the stream delivers is
  a **safe re-expression**: it references only recipe IDs, requirement IDs, and
  drop causes the plan actually produced, and it never restates an
  `evidence-absent` drop as a permissive or compliant statement.
- A recipe whose requirement has **no cost-eligible fresh package** is **dropped
  from the eligible pool with an `evidence-absent` cause** (the inherited
  A-006 drop). The drop is explained at the recipe level alongside the other
  drop causes, distinct from `present-evidence-excludes` and `unmapped`.
- The **user payload excludes audit-only provenance** (R-16's floor:
  `confidence`, `normalization_version`, `source_*` / `*_id`). Every response
  carries a stable **`trace_id`** that references, but never embeds, the
  execution trace.
- An **error** before or during the stream is surfaced as an `error` event with
  a stable code and a human-readable message, consistent with the API's standard
  error envelope; the stream then closes.
- The interface is **stateless per turn**: the response is a function of the
  current message plus the optional user context in the request. p3-004 keeps no
  server-side session store; multi-turn continuity, if any, is carried by the
  client through `user_context`.
- The **API documentation's `/chat` section (§3) is updated** so the
  `plan_updated` example carries the delta **and** the meal-scoped three-level
  explanation (p3-002 C-2), replacing the legacy delta-only example.

## Acceptance criteria

- **AC-1** Given a `POST /chat` request conforming to p3-002's request schema
  (session identifier + message, optional user context), when it is served, then
  the endpoint accepts it and begins an SSE stream whose `Content-Type` is
  `text/event-stream`; a request missing the session identifier or the message
  is rejected before the stream begins.

- **AC-2** Given a served `/chat` turn, when the emitted events are examined,
  then every event's type is exactly one of p3-002's five
  (`metadata`, `token`, `plan_updated`, `error`, `done`), and no event type
  outside that vocabulary is emitted.

- **AC-3** Given a natural-language message stating one or more constraints
  (e.g., an allergen, a dietary flag, a nutrient bound, a horizon), when the turn
  is processed, then those constraints are extracted and applied to the plan
  request, and a constraint the message did not state is not fabricated.

- **AC-4** Given a message that expresses a **cost or budget intent** (e.g., a
  price ceiling, "cheapest", "how much does it cost"), when the turn is
  processed, then a cost intent is detected and cost is surfaced on the turn for
  the recipe and/or ingredient names in scope.

- **AC-5** Given a message that expresses **no cost or budget intent**, when the
  turn is processed, then no cost intent is detected and no cost figure is
  surfaced in the response.

- **AC-6** Given a cost-intent turn whose scoped names are cost-computable, when
  cost is surfaced, then the consumed-ingredient cost is reported separately from
  the whole-package retail price (R-11), computed through the existing
  calculator service rather than recomputed by a parallel code path.

- **AC-7** Given a cost-intent turn in which a requirement has **no cost-eligible
  fresh package** (the calculator's `MISSING_PACKAGE_DATA` condition), when cost
  is surfaced, then the response reports the missing-package condition and does
  not present a fabricated or zero price for that requirement.

- **AC-8** Given a requirement with **no cost-eligible fresh package**, when the
  plan's eligible pool is formed, then the recipe is **dropped from the eligible
  pool with an `evidence-absent` cause** (the inherited A-006 recipe-level
  drop), and the drop is enforced in the api plan service layer. (Satisfies
  R-8's and R-10's recipe-level fixtures.)

- **AC-9** Given a package whose `freshness_status` is not `fresh`, when the
  recipe-level cost drop is evaluated, then the non-fresh offer is treated as
  unavailable and, if no fresh offer remains for the requirement, the recipe is
  dropped with an `evidence-absent` cause (R-8 recipe-level).

- **AC-10** Given a package whose `price_status` is not `estimated`, whose
  `price_match_status` is not `accepted`, or whose `price_basis` is outside the
  cost-convertible set (`package_mass`, `package_volume`), when the recipe-level
  cost drop is evaluated, then that package is ineligible and, if no eligible
  package remains for the requirement, the recipe is dropped with an
  `evidence-absent` cause (R-10 recipe-level).

- **AC-11** Given a plan whose recipe-level and constraint-level outcomes are
  produced, when the user text is generated, then the text references only recipe
  IDs, requirement IDs, and drop causes present in the plan's outcomes; a
  generation referencing an identifier or cause the plan did not produce is
  rejected.

- **AC-12** Given a recipe the plan dropped for **absent evidence** (including
  the inherited cost drop), when the user text is generated, then the text does
  not restate that drop as a permissive, compliant, or "included" statement, and
  the recipe is not presented as selected.

- **AC-13** Given a served recommendation, when the streamed explanation is
  examined, then all three levels — plan, recipe, constraint — are present, and a
  response missing any one level is non-conforming (R-17).

- **AC-14** Given a recipe dropped for absent evidence and a recipe dropped
  because present evidence ruled it out, when their recipe-level explanations are
  examined, then the first carries the `evidence-absent` cause and the second
  carries the `present-evidence-excludes` cause, reported distinctly, with
  `unmapped` distinct from both (R-17).

- **AC-15** Given any served `/chat` response, when the user payload is examined,
  then it contains no `confidence`, no `normalization_version`, and no
  `source_*` / `*_id` provenance field (R-16's floor); a payload in which any
  such field appears is non-conforming.

- **AC-16** Given any served `/chat` response, when the stream is examined, then
  a stable `trace_id` is present that correlates the response with its execution
  trace, and the trace itself is not embedded in any event payload.

- **AC-17** Given a workflow failure (an exception or a failure outcome from any
  node), when the turn is served, then an `error` event with a stable code and a
  human-readable message is emitted and the stream closes, and no partial
  recommendation is presented as complete.

- **AC-18** Given a `plan_updated` event emitted on a turn that changes a meal,
  when its payload is examined, then it carries the delta identifying the changed
  meal (`day`, `slot`, `recipe_id`) and the three-level explanation scoped to
  that meal (p3-002 C-2); a `plan_updated` event with the delta only, or with the
  full-plan explanation, is non-conforming.

- **AC-19** Given two identical `/chat` requests sent independently with no
  shared server state, when both are served, then each is evaluated solely from
  its own message and user context (stateless per turn); the response to the
  second request does not depend on the first having been sent.

- **AC-20** Given the constitution's named fixtures at the A-007 paths
  (`SystemCode/remy/app/tests/api/test_response_schema.py` for R-16 and
  `SystemCode/remy/app/tests/api/test_explanation_shape.py` for R-17), when
  conformance is run against the served `/chat` surface, then both fixtures pass
  for the endpoint's response — the R-16 fixture passing both its clauses
  (user-payload exclusion and trace-side retention; F-P3-1 was resolved
  2026-10-17).

- **AC-21** Given the API documentation's `/chat` section (§3), when it is
  examined after this feature, then its `plan_updated` example carries the delta
  **and** the meal-scoped three-level explanation (p3-002 C-2), not the legacy
  delta-only example.

## Edge cases & errors

- **Ambiguous cost intent.** A message whose cost intent is unclear is resolved
  conservatively: if no affordability/price reference is present, no cost is
  surfaced (AC-5). The boundary of what counts as a cost intent is a plan-stage
  detail; the spec requires only that an explicit price/affordability reference
  triggers cost and its absence does not.
- **Cost intent but no scoped names.** A cost-intent turn with no resolvable
  recipe or ingredient name surfaces no price and is not an error; the
  explanation proceeds without cost figures.
- **No fresh / no eligible package for a requirement.** The requirement surfaces
  `MISSING_PACKAGE_DATA` at the item level (AC-7) and the recipe is dropped at
  the recipe level with an `evidence-absent` cause (AC-8/AC-9/AC-10).
- **All recipes dropped by the cost drop.** If the inherited cost drop empties
  the eligible pool, the plan returns infeasible with its binding constraint(s)
  named (R-14 output, unchanged); the surface renders that outcome, it does not
  fabricate a plan.
- **Workflow failure mid-stream.** Surfaced as an `error` event with a stable
  code; the stream closes; no partial recommendation is presented as complete
  (AC-17).
- **Generation references an unknown identifier or cause.** The generation is
  rejected by the Generate Response node's deterministic check (AC-11); the turn
  does not emit fabricated references.
- **Evidence-absent restated as permissive.** Rejected by the safe re-expression
  check (AC-12); an evidence-absent recipe is never presented as selected.
- **Provenance leak attempt.** Any user-facing field carrying `confidence`,
  `normalization_version`, or a `source_*` / `*_id` value makes the payload
  non-conforming (AC-15).
- **Trace embedded in the stream.** Any event carrying the trace itself is
  non-conforming; the trace is referenced by `trace_id` only (AC-16).
- **Unknown or extra SSE event type.** An event whose type is not one of
  p3-002's five is non-conforming (AC-2).
- **Multi-turn request relying on server memory.** Not supported; continuity is
  the client's to carry via `user_context` (AC-19).
- **Partial-coverage data (DQ-1..DQ-7).** The surface explains whatever the plan
  produced; it neither compensates for nor masks coverage gaps.

## Non-goals

- **Session or state persistence.** p3-004 is stateless per turn; it builds no
  server-side session store and no cross-turn memory.
- **Redefining p3-002's schemas or adding SSE event types.** p3-004 implements
  the existing request, event, and explanation schemas; it adds no new event
  type and changes no field contract.
- **Re-deciding p2's reasoning or drop causes.** The three-level outcomes, the
  drop causes (`evidence-absent`, `present-evidence-excludes`, `unmapped`), and
  their precedence are produced upstream; p3-004 surfaces them, it does not
  recompute them.
- **Compensating for the data-quality findings DQ-1..DQ-7.** Coverage gaps are
  upstream of this feature and are neither closed nor masked here.
- **The web planner experience (p3-003).** A separate frontend effort consumes
  this surface; p3-004 does not build the web UI.
- **The judge/eval layer's implementation.** p3-004 preserves the trace
  identifier and structured references that a future judge/eval layer will
  consume; it defines no judge endpoint, storage, or metric.
- **Designing the concrete modules, data structures, field names, or test
  internals.** Those are plan-stage decisions; this spec names the behavior and
  the required fields/shapes, not their implementation.

## Interfaces & dependencies

### Surfaces owned / implemented by p3-004

| Surface | p3-004's relationship |
|---|---|
| `POST /api/v1/chat` endpoint + SSE transport (in `remy/app`) | **p3-004 implements** p3-002's request + event schemas; opens/frames/closes the stream |
| Cost/budget intent detection on the extracted constraints | **p3-004 adds** intent detection extending the extraction node's output |
| On-demand cost for recipe/ingredient names | **p3-004 calls** the existing calculator service; does not reimplement cost |
| Recipe-level cost drop (A-006) in the api plan service | **p3-004 lands** the drop (evidence-absent) and asserts R-8/R-10 recipe-level fixtures |
| Safe re-expression of explanation causes | **p3-004 reuses** p3-001's Generate Response node and its deterministic check |
| API_doc §3 `plan_updated` update | **p3-004 updates** the doc to delta + meal-scoped explanation (p3-002 C-2 / N-2) |

### Consumed (not redefined)

- **p3-002** — the `/chat` request schema, the five SSE event schemas, the
  three-level explanation shape, the `trace_id` boundary, and the R-16 forbidden
  field floor. p3-004 serves these shapes; it does not change them.
- **p3-001** — the LangGraph workflow (Extract Constraints, Plan, Generate
  Response), the versioned `TraceEnvelope`, and the plan port/adapter boundary.
  p3-004 runs this workflow and reuses Generate Response for safe re-expression.
- **p2 calculator** — the cost/nutrition service, which computes consumed vs.
  retail package cost and emits item-level `MISSING_PACKAGE_DATA` /
  `PARTIAL_NUTRITION_DATA`. p3-004 consumes it for on-demand cost.
- **p2 plan service** — the layer in which the inherited A-006 recipe-level cost
  drop is enforced; p3-004's drop consumes the calculator's
  `MISSING_PACKAGE_DATA` as the evidence-absent signal.

### Named fixtures (A-007 paths)

- R-16 and R-17 conformance for the `/chat` surface is asserted at
  `SystemCode/remy/app/tests/api/test_response_schema.py` and
  `SystemCode/remy/app/tests/api/test_explanation_shape.py` (per A-007).
- The recipe-level cost-drop fixtures (R-8/R-10 recipe-level) live with the plan
  feature at `SystemCode/remy/api/tests/features/plan/` (per A-006).
- The precise test module layout and the chat-contract fixtures beyond the named
  ones are plan-stage decisions.

### Dependency direction (R-2)

- The `/chat` endpoint lives in `remy/app` because it composes `api` and
  `workflows`, and `api` may not import `app`. The `.importlinter` contracts must
  continue to pass.

### Runtime / data dependency

- The plan path reads the canonical graph, subject to the tracked
  `data-prep-price-path` finding and DQ-1..DQ-7. Conformance evidence uses the
  phase's approved fixtures; the surface explains whatever the plan produces.

## Open questions

<!-- No blocking open questions. The seven pre-confirmed human decisions are
     recorded under ## Clarifications and are not reopened. -->

## Clarifications

- **C-1 (A-006 drop layer: api plan service, 2026-10-18, human).** The inherited
  recipe-level cost drop (A-006) is enforced in the **api plan service** layer
  (the plan feature's service/filtering), consuming the calculator's item-level
  `MISSING_PACKAGE_DATA` signal as the evidence-absent evidence; its fixtures
  live at `SystemCode/remy/api/tests/features/plan/`. Rationale: the plan service
  is the layer that forms the eligible pool and already applies the other
  recipe-level drops, so the cost drop is cohesive there. **Consequential — flag
  for `decisions.md` at close.**
- **C-2 (stateless per turn, 2026-10-18, human).** The `/chat` interface keeps no
  server-side session store; each turn is evaluated from its own message and
  optional `user_context`. Multi-turn continuity, if any, is carried by the
  client. Rationale: avoids introducing a session store and the associated
  persistence contract, which are out of scope for this phase. **Consequential —
  flag for `decisions.md` at close.**
- **C-3 (reuse p3-001 Generate Response for safe re-expression, 2026-10-18,
  human).** The safe re-expression of explanation causes reuses p3-001's Generate
  Response node and its deterministic structured-output check (referenced
  IDs/causes must be a subset of the plan's; evidence-absent never restated as
  permissive) rather than introducing a new generation path. Rationale: the node
  already enforces the safety invariant; re-implementing it would risk
  divergence. **Consequential — flag for `decisions.md` at close.**
- **C-4 (DQ-1..DQ-7 accepted, not compensated, 2026-10-18, human).** The phase p2
  data-quality findings (DQ-1..DQ-7) are accepted as tracked data-preparation
  follow-ups; p3-004 builds against whatever the plan produces and does not
  compensate for coverage gaps. Rationale: coverage is upstream of this feature;
  compensating would mask the findings. **Consequential — flag for
  `decisions.md` at close.**
- **C-5 (D-a: cost folded into `/chat` using the existing response shape,
  2026-10-18, human).** On-demand cost is surfaced by folding it into the
  existing p3-002 `/chat` response (the `ChatResponseEnvelope` projection and the
  SSE event payloads), not by adding a new response type or a parallel cost
  endpoint. Rationale: keeps the one conversational surface and reuses the frozen
  contract. **Consequential — flag for `decisions.md` at close.**
- **C-6 (D-b: intent detection extends the extraction node output with an
  optional cost-query field, 2026-10-18, human).** Cost/budget intent detection
  is realized by extending p3-001's Extract Constraints output with an optional
  cost-query field, rather than by a separate classifier stage. Rationale: intent
  is extracted from the same message the node already parses; a co-located field
  keeps the workflow's node count unchanged. The concrete field name and type are
  plan-stage decisions. **Consequential — flag for `decisions.md` at close.**
- **C-7 (A-007 fixture paths adopted, 2026-10-18, human).** p3-004 asserts R-16
  and R-17 for the `/chat` surface at the A-007 paths
  (`SystemCode/remy/app/tests/api/test_response_schema.py`,
  `SystemCode/remy/app/tests/api/test_explanation_shape.py`), where `remy/app` is
  importable. Rationale: the contract types live in `remy/app` (the only package
  permitted to import both `api` and `workflows`), so the fixtures must run
  there. **Consequential — flag for `decisions.md` at close.**---
  feature: p3-004-conversational-constraint-interface
---

# Spec - Conversational constraint interface

## Summary

This feature **implements** the conversational recommendation surface the
earlier p3 features defined but did not build. Concretely, p3-004:

1. **Serves `POST /chat`** as a Server-Sent Events (SSE) endpoint that accepts a
   natural-language request, runs the p3-001 LangGraph workflow, and streams the
   p3-002 event vocabulary (`metadata`, `token`, `plan_updated`, `error`,
   `done`) back to the caller. The endpoint and its SSE transport live in
   `remy/app`, the only package permitted to import both `api` and `workflows`
   (R-2; p3-002 F-1).
2. **Extracts constraints from natural language** and detects a **cost/budget
   intent**, so that a request that asks about affordability ("under $5",
   "cheapest option", "what does this cost") is recognized and surfaces cost on
   the turn, while a request that does not mention cost does not.
3. **Re-expresses the deterministic explanation causes safely.** The workflow's
   Generate Response node (p3-001) is reused to turn the plan/recipe/constraint
   outcomes into user text without paraphrasing an `evidence-absent` drop into a
   permissive statement, and without inventing recipe IDs, requirement IDs, or
   drop causes the plan did not produce.
4. **Lands the recipe-level cost drop inherited from A-006.** When a requirement
   has no cost-eligible, fresh package (the calculator's `MISSING_PACKAGE_DATA`
   signal, per amended R-8/R-10), the recipe is dropped from the eligible pool
   with an `evidence-absent` cause, closing the R-8/R-10 recipe-level check
   obligation deferred from p2. This drop is enforced in the **api plan
   service** layer.

p3-004 **implements against** three frozen contracts and does not redefine them:
p3-002's request/event/explanation schemas (the *shape* of the surface),
p3-001's workflow nodes and `TraceEnvelope` (the *reasoning* the surface
delivers), and p2's reasoning and drop causes (the *outcomes* the surface
re-expresses). It is stateless per turn: each request is evaluated on its own
message and optional user context, with no server-side session memory.

**Phase p2 closed with the data-quality findings DQ-1..DQ-7 tracked, not
blocking.** p3-004 builds against whatever the plan produces; it does not
compensate for coverage gaps.

## Traces to

- **G-1 (budget aspect)** — "Feasible, budget-aware meal plans." p3-004 closes
  the R-8/R-10 recipe-level cost-drop obligation A-006 deferred from p2: a
  recipe whose requirement has no cost-eligible fresh package is dropped with an
  `evidence-absent` cause, and the conversational surface surfaces cost on a
  budget-intent turn.
- **G-2 (explainable recommendations)** — the conversational surface delivers
  the three-level explanation (plan / recipe / constraint) to the user and
  re-expresses the drop causes without softening them into permissive
  statements.
- **G-6 (transparent, auditable reasoning)** — every streamed response carries a
  stable `trace_id` referencing (never embedding) the execution trace; the user
  payload excludes R-16's audit-only provenance floor.
- **Roadmap phase p3 → p3-004-conversational-constraint-interface** *(new)* —
  "Conversational constraint extraction, turn-level recommendation delivery, and
  safe re-expression of deterministic explanation causes. **Additionally,
  p3-004 inherits the recipe-level cost drop from A-006**: when a requirement
  has no cost-eligible package (the calculator's `MISSING_PACKAGE_DATA` signal,
  per amended R-8/R-10), p3-004 drops the recipe from the eligible pool with an
  evidence-absent cause, asserting R-8's and R-10's recipe-level fixtures."
- **Phase p3 outcome** — "a conversational interface accepts natural-language
  requests, preserves the deterministic explanation causes, and surfaces cost on
  follow-up turns."
- **Phase p3 exit criteria** — "The conversational interface extracts
  constraints from natural language, delivers turn-level recommendations, and
  re-expresses explanation causes without paraphrasing them into permissive
  statements"; and "Cost and budget evaluation is in scope for p3-004 (per
  A-006); R-8's and R-10's recipe-level fixtures are satisfied by p3-004."
- **Roadmap shared contract** — "Conversational constraint extraction,
  turn-level recommendation delivery, safe re-expression of deterministic
  explanation causes, and the recipe-level cost drop inherited from R-8/R-10 per
  A-006," shared with p3-001, p3-002, and p3-003.
- **Constitutional rules** (constitution v1.7):
  - **R-8** (non-fresh price offers are unavailable) — p3-004 owns the
    recipe-level cost drop: a requirement left with no fresh package (the
    calculator's `MISSING_PACKAGE_DATA` signal) drops the recipe with an
    `evidence-absent` cause. p3-004 satisfies R-8's recipe-level fixture.
  - **R-10** (cost eligibility requires a convertible price basis) — p3-004 owns
    the recipe-level cost drop when no cost-eligible package exists for a
    requirement. p3-004 satisfies R-10's recipe-level fixture.
  - **R-16** (user response excludes audit-only provenance) — the `/chat` user
    payload exposes only the resolved food concept, chosen offer, per-requirement
    constraint outcome, and warned conditions; it excludes `confidence`,
    `normalization_version`, and any `source_*` / `*_id` provenance (R-16's
    floor), which is retained only in the trace.
  - **R-17** (three-level explanations with distinct drop causes) — the `/chat`
    surface exposes plan, recipe, and constraint granularity including dropped
    candidates, with `evidence-absent` reported distinctly from
    `present-evidence-excludes` and `unmapped`.
  - **R-2** (inward dependency direction) — the `/chat` endpoint lives in
    `remy/app`; the `.importlinter` contracts ("api does not depend on app")
    continue to pass.
  - **R-13** (selection by best score, confidence in trace) — p3-004 does not
    re-decide selection; it surfaces the plan's outcomes.
- **Amendments:**
  - **A-006** assigns p3-004 the recipe-level cost drop and the R-8/R-10
    recipe-level check obligation, enforced in the api plan service layer.
  - **A-007** fixes R-16's and R-17's named check paths to
    `SystemCode/remy/app/tests/api/<name>`; p3-004 asserts against those paths.

## User-facing behavior

- A caller sends a `POST /chat` request carrying a **session identifier**, a
  **message** (natural language), and an optional **user context** (for example,
  a current plan identifier). The request conforms to p3-002's `/chat` request
  schema; p3-004 serves it and does not redefine it.
- The server responds with a **stream of events** drawn only from p3-002's fixed
  vocabulary: `metadata`, `token`, `plan_updated`, `error`, `done`. p3-004 opens,
  frames, and closes the stream; it adds no new event type.
- p3-004 **extracts the request's constraints from natural language** (nutrient
  bounds, allergens, dietary flags, horizon/meals, tolerance) by running the
  p3-001 Extract Constraints node, and additionally **detects whether the turn
  expresses a cost or budget intent**. A message that references affordability,
  a price ceiling, or "what does it cost" carries a cost intent; a message with
  no cost reference does not.
- When the turn **carries a cost intent**, the response **surfaces cost** for
  the recipe and/or ingredient names in scope, computed on demand through the
  existing calculator service (consumed cost distinct from retail package cost,
  per R-11). A requirement with no cost-eligible fresh package surfaces the
  calculator's `MISSING_PACKAGE_DATA` condition rather than a fabricated price.
- When the turn **does not carry a cost intent**, cost is not computed or
  surfaced; the response is the plan/recipe/constraint explanation without cost
  figures.
- The **recommendation is exposed at three levels** — plan, recipe, constraint —
  with dropped candidates always explained. The user text the stream delivers is
  a **safe re-expression**: it references only recipe IDs, requirement IDs, and
  drop causes the plan actually produced, and it never restates an
  `evidence-absent` drop as a permissive or compliant statement.
- A recipe whose requirement has **no cost-eligible fresh package** is **dropped
  from the eligible pool with an `evidence-absent` cause** (the inherited
  A-006 drop). The drop is explained at the recipe level alongside the other
  drop causes, distinct from `present-evidence-excludes` and `unmapped`.
- The **user payload excludes audit-only provenance** (R-16's floor:
  `confidence`, `normalization_version`, `source_*` / `*_id`). Every response
  carries a stable **`trace_id`** that references, but never embeds, the
  execution trace.
- An **error** before or during the stream is surfaced as an `error` event with
  a stable code and a human-readable message, consistent with the API's standard
  error envelope; the stream then closes.
- The interface is **stateless per turn**: the response is a function of the
  current message plus the optional user context in the request. p3-004 keeps no
  server-side session store; multi-turn continuity, if any, is carried by the
  client through `user_context`.
- The **API documentation's `/chat` section (§3) is updated** so the
  `plan_updated` example carries the delta **and** the meal-scoped three-level
  explanation (p3-002 C-2), replacing the legacy delta-only example.

## Acceptance criteria

- **AC-1** Given a `POST /chat` request conforming to p3-002's request schema
  (session identifier + message, optional user context), when it is served, then
  the endpoint accepts it and begins an SSE stream whose `Content-Type` is
  `text/event-stream`; a request missing the session identifier or the message
  is rejected before the stream begins.

- **AC-2** Given a served `/chat` turn, when the emitted events are examined,
  then every event's type is exactly one of p3-002's five
  (`metadata`, `token`, `plan_updated`, `error`, `done`), and no event type
  outside that vocabulary is emitted.

- **AC-3** Given a natural-language message stating one or more constraints
  (e.g., an allergen, a dietary flag, a nutrient bound, a horizon), when the turn
  is processed, then those constraints are extracted and applied to the plan
  request, and a constraint the message did not state is not fabricated.

- **AC-4** Given a message that expresses a **cost or budget intent** (e.g., a
  price ceiling, "cheapest", "how much does it cost"), when the turn is
  processed, then a cost intent is detected and cost is surfaced on the turn for
  the recipe and/or ingredient names in scope.

- **AC-5** Given a message that expresses **no cost or budget intent**, when the
  turn is processed, then no cost intent is detected and no cost figure is
  surfaced in the response.

- **AC-6** Given a cost-intent turn whose scoped names are cost-computable, when
  cost is surfaced, then the consumed-ingredient cost is reported separately from
  the whole-package retail price (R-11), computed through the existing
  calculator service rather than recomputed by a parallel code path.

- **AC-7** Given a cost-intent turn in which a requirement has **no cost-eligible
  fresh package** (the calculator's `MISSING_PACKAGE_DATA` condition), when cost
  is surfaced, then the response reports the missing-package condition and does
  not present a fabricated or zero price for that requirement.

- **AC-8** Given a requirement with **no cost-eligible fresh package**, when the
  plan's eligible pool is formed, then the recipe is **dropped from the eligible
  pool with an `evidence-absent` cause** (the inherited A-006 recipe-level
  drop), and the drop is enforced in the api plan service layer. (Satisfies
  R-8's and R-10's recipe-level fixtures.)

- **AC-9** Given a package whose `freshness_status` is not `fresh`, when the
  recipe-level cost drop is evaluated, then the non-fresh offer is treated as
  unavailable and, if no fresh offer remains for the requirement, the recipe is
  dropped with an `evidence-absent` cause (R-8 recipe-level).

- **AC-10** Given a package whose `price_status` is not `estimated`, whose
  `price_match_status` is not `accepted`, or whose `price_basis` is outside the
  cost-convertible set (`package_mass`, `package_volume`), when the recipe-level
  cost drop is evaluated, then that package is ineligible and, if no eligible
  package remains for the requirement, the recipe is dropped with an
  `evidence-absent` cause (R-10 recipe-level).

- **AC-11** Given a plan whose recipe-level and constraint-level outcomes are
  produced, when the user text is generated, then the text references only recipe
  IDs, requirement IDs, and drop causes present in the plan's outcomes; a
  generation referencing an identifier or cause the plan did not produce is
  rejected.

- **AC-12** Given a recipe the plan dropped for **absent evidence** (including
  the inherited cost drop), when the user text is generated, then the text does
  not restate that drop as a permissive, compliant, or "included" statement, and
  the recipe is not presented as selected.

- **AC-13** Given a served recommendation, when the streamed explanation is
  examined, then all three levels — plan, recipe, constraint — are present, and a
  response missing any one level is non-conforming (R-17).

- **AC-14** Given a recipe dropped for absent evidence and a recipe dropped
  because present evidence ruled it out, when their recipe-level explanations are
  examined, then the first carries the `evidence-absent` cause and the second
  carries the `present-evidence-excludes` cause, reported distinctly, with
  `unmapped` distinct from both (R-17).

- **AC-15** Given any served `/chat` response, when the user payload is examined,
  then it contains no `confidence`, no `normalization_version`, and no
  `source_*` / `*_id` provenance field (R-16's floor); a payload in which any
  such field appears is non-conforming.

- **AC-16** Given any served `/chat` response, when the stream is examined, then
  a stable `trace_id` is present that correlates the response with its execution
  trace, and the trace itself is not embedded in any event payload.

- **AC-17** Given a workflow failure (an exception or a failure outcome from any
  node), when the turn is served, then an `error` event with a stable code and a
  human-readable message is emitted and the stream closes, and no partial
  recommendation is presented as complete.

- **AC-18** Given a `plan_updated` event emitted on a turn that changes a meal,
  when its payload is examined, then it carries the delta identifying the changed
  meal (`day`, `slot`, `recipe_id`) and the three-level explanation scoped to
  that meal (p3-002 C-2); a `plan_updated` event with the delta only, or with the
  full-plan explanation, is non-conforming.

- **AC-19** Given two identical `/chat` requests sent independently with no
  shared server state, when both are served, then each is evaluated solely from
  its own message and user context (stateless per turn); the response to the
  second request does not depend on the first having been sent.

- **AC-20** Given the constitution's named fixtures at the A-007 paths
  (`SystemCode/remy/app/tests/api/test_response_schema.py` for R-16 and
  `SystemCode/remy/app/tests/api/test_explanation_shape.py` for R-17), when
  conformance is run against the served `/chat` surface, then both fixtures pass
  for the endpoint's response — the R-16 fixture passing both its clauses
  (user-payload exclusion and trace-side retention; F-P3-1 was resolved
  2026-10-17).

- **AC-21** Given the API documentation's `/chat` section (§3), when it is
  examined after this feature, then its `plan_updated` example carries the delta
  **and** the meal-scoped three-level explanation (p3-002 C-2), not the legacy
  delta-only example.

## Edge cases & errors

- **Ambiguous cost intent.** A message whose cost intent is unclear is resolved
  conservatively: if no affordability/price reference is present, no cost is
  surfaced (AC-5). The boundary of what counts as a cost intent is a plan-stage
  detail; the spec requires only that an explicit price/affordability reference
  triggers cost and its absence does not.
- **Cost intent but no scoped names.** A cost-intent turn with no resolvable
  recipe or ingredient name surfaces no price and is not an error; the
  explanation proceeds without cost figures.
- **No fresh / no eligible package for a requirement.** The requirement surfaces
  `MISSING_PACKAGE_DATA` at the item level (AC-7) and the recipe is dropped at
  the recipe level with an `evidence-absent` cause (AC-8/AC-9/AC-10).
- **All recipes dropped by the cost drop.** If the inherited cost drop empties
  the eligible pool, the plan returns infeasible with its binding constraint(s)
  named (R-14 output, unchanged); the surface renders that outcome, it does not
  fabricate a plan.
- **Workflow failure mid-stream.** Surfaced as an `error` event with a stable
  code; the stream closes; no partial recommendation is presented as complete
  (AC-17).
- **Generation references an unknown identifier or cause.** The generation is
  rejected by the Generate Response node's deterministic check (AC-11); the turn
  does not emit fabricated references.
- **Evidence-absent restated as permissive.** Rejected by the safe re-expression
  check (AC-12); an evidence-absent recipe is never presented as selected.
- **Provenance leak attempt.** Any user-facing field carrying `confidence`,
  `normalization_version`, or a `source_*` / `*_id` value makes the payload
  non-conforming (AC-15).
- **Trace embedded in the stream.** Any event carrying the trace itself is
  non-conforming; the trace is referenced by `trace_id` only (AC-16).
- **Unknown or extra SSE event type.** An event whose type is not one of
  p3-002's five is non-conforming (AC-2).
- **Multi-turn request relying on server memory.** Not supported; continuity is
  the client's to carry via `user_context` (AC-19).
- **Partial-coverage data (DQ-1..DQ-7).** The surface explains whatever the plan
  produced; it neither compensates for nor masks coverage gaps.

## Non-goals

- **Session or state persistence.** p3-004 is stateless per turn; it builds no
  server-side session store and no cross-turn memory.
- **Redefining p3-002's schemas or adding SSE event types.** p3-004 implements
  the existing request, event, and explanation schemas; it adds no new event
  type and changes no field contract.
- **Re-deciding p2's reasoning or drop causes.** The three-level outcomes, the
  drop causes (`evidence-absent`, `present-evidence-excludes`, `unmapped`), and
  their precedence are produced upstream; p3-004 surfaces them, it does not
  recompute them.
- **Compensating for the data-quality findings DQ-1..DQ-7.** Coverage gaps are
  upstream of this feature and are neither closed nor masked here.
- **The web planner experience (p3-003).** A separate frontend effort consumes
  this surface; p3-004 does not build the web UI.
- **The judge/eval layer's implementation.** p3-004 preserves the trace
  identifier and structured references that a future judge/eval layer will
  consume; it defines no judge endpoint, storage, or metric.
- **Designing the concrete modules, data structures, field names, or test
  internals.** Those are plan-stage decisions; this spec names the behavior and
  the required fields/shapes, not their implementation.

## Interfaces & dependencies

### Surfaces owned / implemented by p3-004

| Surface | p3-004's relationship |
|---|---|
| `POST /api/v1/chat` endpoint + SSE transport (in `remy/app`) | **p3-004 implements** p3-002's request + event schemas; opens/frames/closes the stream |
| Cost/budget intent detection on the extracted constraints | **p3-004 adds** intent detection extending the extraction node's output |
| On-demand cost for recipe/ingredient names | **p3-004 calls** the existing calculator service; does not reimplement cost |
| Recipe-level cost drop (A-006) in the api plan service | **p3-004 lands** the drop (evidence-absent) and asserts R-8/R-10 recipe-level fixtures |
| Safe re-expression of explanation causes | **p3-004 reuses** p3-001's Generate Response node and its deterministic check |
| API_doc §3 `plan_updated` update | **p3-004 updates** the doc to delta + meal-scoped explanation (p3-002 C-2 / N-2) |

### Consumed (not redefined)

- **p3-002** — the `/chat` request schema, the five SSE event schemas, the
  three-level explanation shape, the `trace_id` boundary, and the R-16 forbidden
  field floor. p3-004 serves these shapes; it does not change them.
- **p3-001** — the LangGraph workflow (Extract Constraints, Plan, Generate
  Response), the versioned `TraceEnvelope`, and the plan port/adapter boundary.
  p3-004 runs this workflow and reuses Generate Response for safe re-expression.
- **p2 calculator** — the cost/nutrition service, which computes consumed vs.
  retail package cost and emits item-level `MISSING_PACKAGE_DATA` /
  `PARTIAL_NUTRITION_DATA`. p3-004 consumes it for on-demand cost.
- **p2 plan service** — the layer in which the inherited A-006 recipe-level cost
  drop is enforced; p3-004's drop consumes the calculator's
  `MISSING_PACKAGE_DATA` as the evidence-absent signal.

### Named fixtures (A-007 paths)

- R-16 and R-17 conformance for the `/chat` surface is asserted at
  `SystemCode/remy/app/tests/api/test_response_schema.py` and
  `SystemCode/remy/app/tests/api/test_explanation_shape.py` (per A-007).
- The recipe-level cost-drop fixtures (R-8/R-10 recipe-level) live with the plan
  feature at `SystemCode/remy/api/tests/features/plan/` (per A-006).
- The precise test module layout and the chat-contract fixtures beyond the named
  ones are plan-stage decisions.

### Dependency direction (R-2)

- The `/chat` endpoint lives in `remy/app` because it composes `api` and
  `workflows`, and `api` may not import `app`. The `.importlinter` contracts must
  continue to pass.

### Runtime / data dependency

- The plan path reads the canonical graph, subject to the tracked
  `data-prep-price-path` finding and DQ-1..DQ-7. Conformance evidence uses the
  phase's approved fixtures; the surface explains whatever the plan produces.

## Open questions

<!-- No blocking open questions. The seven pre-confirmed human decisions are
     recorded under ## Clarifications and are not reopened. -->

## Clarifications

- **C-1 (A-006 drop layer: api plan service, 2026-10-18, human).** The inherited
  recipe-level cost drop (A-006) is enforced in the **api plan service** layer
  (the plan feature's service/filtering), consuming the calculator's item-level
  `MISSING_PACKAGE_DATA` signal as the evidence-absent evidence; its fixtures
  live at `SystemCode/remy/api/tests/features/plan/`. Rationale: the plan service
  is the layer that forms the eligible pool and already applies the other
  recipe-level drops, so the cost drop is cohesive there. **Consequential — flag
  for `decisions.md` at close.**
- **C-2 (stateless per turn, 2026-10-18, human).** The `/chat` interface keeps no
  server-side session store; each turn is evaluated from its own message and
  optional `user_context`. Multi-turn continuity, if any, is carried by the
  client. Rationale: avoids introducing a session store and the associated
  persistence contract, which are out of scope for this phase. **Consequential —
  flag for `decisions.md` at close.**
- **C-3 (reuse p3-001 Generate Response for safe re-expression, 2026-10-18,
  human).** The safe re-expression of explanation causes reuses p3-001's Generate
  Response node and its deterministic structured-output check (referenced
  IDs/causes must be a subset of the plan's; evidence-absent never restated as
  permissive) rather than introducing a new generation path. Rationale: the node
  already enforces the safety invariant; re-implementing it would risk
  divergence. **Consequential — flag for `decisions.md` at close.**
- **C-4 (DQ-1..DQ-7 accepted, not compensated, 2026-10-18, human).** The phase p2
  data-quality findings (DQ-1..DQ-7) are accepted as tracked data-preparation
  follow-ups; p3-004 builds against whatever the plan produces and does not
  compensate for coverage gaps. Rationale: coverage is upstream of this feature;
  compensating would mask the findings. **Consequential — flag for
  `decisions.md` at close.**
- **C-5 (D-a: cost folded into `/chat` using the existing response shape,
  2026-10-18, human).** On-demand cost is surfaced by folding it into the
  existing p3-002 `/chat` response (the `ChatResponseEnvelope` projection and the
  SSE event payloads), not by adding a new response type or a parallel cost
  endpoint. Rationale: keeps the one conversational surface and reuses the frozen
  contract. **Consequential — flag for `decisions.md` at close.**
- **C-6 (D-b: intent detection extends the extraction node output with an
  optional cost-query field, 2026-10-18, human).** Cost/budget intent detection
  is realized by extending p3-001's Extract Constraints output with an optional
  cost-query field, rather than by a separate classifier stage. Rationale: intent
  is extracted from the same message the node already parses; a co-located field
  keeps the workflow's node count unchanged. The concrete field name and type are
  plan-stage decisions. **Consequential — flag for `decisions.md` at close.**
- **C-7 (A-007 fixture paths adopted, 2026-10-18, human).** p3-004 asserts R-16
  and R-17 for the `/chat` surface at the A-007 paths
  (`SystemCode/remy/app/tests/api/test_response_schema.py`,
  `SystemCode/remy/app/tests/api/test_explanation_shape.py`), where `remy/app` is
  importable. Rationale: the contract types live in `remy/app` (the only package
  permitted to import both `api` and `workflows`), so the fixtures must run
  there. **Consequential — flag for `decisions.md` at close.**
