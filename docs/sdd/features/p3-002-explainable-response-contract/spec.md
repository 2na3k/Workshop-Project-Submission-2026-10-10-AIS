---
feature: p3-002-explainable-response-contract
---

# Spec - Explainable response contract

## Summary

This feature defines the **user-facing response contract** for Remy's
conversational recommendation surface: the request shape, the Server-Sent
Events (SSE) event shapes, the three-level explanation shape (plan / recipe /
constraint), and the boundary that keeps audit-only provenance out of the user
payload. **It is a contract, not an implementation.** p3-002 defines the shapes
that the conversational surface (p3-004) implements against and that the web
surface (p3-003) consumes; it does not build the `/chat` endpoint, the SSE
transport, any workflow node, or the web planner.

The contract sits between the workflow (p3-001) and the delivery surfaces
(p3-003, p3-004). Its input is p3-001's `TraceEnvelope` — a versioned envelope
carrying the workflow `Outcome` (`plan | infeasible | failure`), the raw
message, the parsed constraint set, the unapplied constraints, one record per
node run, one record per LLM invocation, and the embedded `PlanTraceView`. Its
output is the shape a caller observes: a request schema for `/chat`; five SSE
event schemas (`metadata`, `token`, `plan_updated`, `error`, `done`); a
three-level explanation shape with the drop causes p2 established
(`evidence-absent`, `present-evidence-excludes`, `unmapped`) and their
precedence; the audit-provenance boundary; and the trace-identifier and
retrieval guarantee that a downstream judge/eval layer consumes.

The constitution's two explainability rules are realized here as their two
**named fixtures**, which do not yet exist in the codebase and are created by
this feature at the constitution's named paths: `tests/api/test_response_schema.py`
(R-16) and `tests/api/test_explanation_shape.py` (R-17). The R-16 fixture
asserts both clauses of the rule: that the user-facing payload excludes
`confidence`, `normalization_version`, and `source_*` / `*_id` provenance, and
that those fields are retained in the trace object. The R-17 fixture asserts
that all three explanation levels are present and that an `evidence-absent`
drop is reported distinctly from a `present-evidence-excludes` drop.

**p3-002 re-decides none of p2's reasoning.** The three-level outcomes, the
drop causes, and their precedence are produced upstream (p2-001, p2-003) and
surfaced by p3-001's trace; this feature defines how that reasoning is *shaped*
for the user, not how it is *computed*. The contract carries p2's outcomes
through without softening, re-ordering, or collapsing them.

**Phase p2 closed with data-coverage findings (DQ-1..DQ-7) tracked, not
blocking.** p3-002's conformance fixtures operate on the *shape* the workflow
produces; the plan's output quality is upstream and is neither compensated for
nor masked by this contract.

**Trace-side provenance reach is limited by Finding F-P3-1.** p3-001 records
that `PlanTrace` (hence the embedded `PlanTraceView`) carries no mapping
confidence, normalization version, or source identifiers — the audit provenance
R-16's trace-side clause requires. Until F-P3-1 resolves (a p2-002 reopen
extending the offer reference plus a p2-003 propagation), R-16's trace-side
assertion in this feature's fixture is `xfail` with a reason referencing
F-P3-1. R-16's user-payload exclusion clause passes regardless, because
exclusion does not depend on the fields being present upstream.

## Traces to

- **G-2** — "Explainable recommendations." This contract exposes the
  recommendation at plan, recipe, and constraint granularity, including dropped
  candidates with their distinct causes, so a recommendation can be explained
  to the user rather than asserted.
- **G-6** — "Transparent, auditable reasoning." This contract draws the
  boundary between what the user sees and what the trace retains: audit-only
  provenance stays in the trace, and a stable identifier correlates the
  user-visible response with its trace for a downstream judge/eval layer.
  **G-6's trace-side auditability is limited by Finding F-P3-1** — the trace
  carries whatever `PlanTraceView` carries, which currently excludes R-16's
  provenance fields.
- **Roadmap phase p3 → p3-002-explainable-response-contract** *(new)* — "The
  user-facing response contract exposing three-level explanations (plan,
  recipe, constraint) with the drop causes p2 established (`evidence-absent`,
  `present-evidence-excludes`, `unmapped`), and strict separation of audit-only
  provenance (mapping confidence, normalization version, source identifiers) to
  the execution trace. Consumes p3-001's trace and p2-001/p2-002's outcome
  contracts."
- **Phase p3 outcome** — "a response contract exposes three-level reasoning
  (plan / recipe / constraint) with the drop-cause distinctions p2
  established."
- **Roadmap shared contract** — "Three-level user explanation and
  audit-provenance separation," shared with
  p3-001-workflow-recommendation-service, p3-003-web-planner-experience, and
  p3-004-conversational-constraint-interface.
- **Constitutional rules** (constitution v1.6):
  - **R-16** (user response excludes audit-only provenance) — this feature
    defines the user-facing response shape so that only the resolved food
    concept, chosen offer, per-requirement constraint outcome, and warned
    conditions are exposed, and `confidence`, `normalization_version`, and any
    `source_*` / `*_id` provenance are excluded from the user payload and
    retained only in the trace. **This feature owns R-16's named fixture**
    `tests/api/test_response_schema.py`, asserting both clauses. R-16's
    named four categories are the **floor**; endpoints may carry stricter
    exclusion lists of their own (see "Audit-provenance boundary" below and
    Clarification C-3).
  - **R-17** (three-level explanations with distinct drop causes) — this
    feature defines the explanation shape so that every recommendation exposes
    plan, recipe, and constraint granularity including dropped candidates, with
    an `evidence-absent` drop reported distinctly from a
    `present-evidence-excludes` drop. **This feature owns R-17's named fixture**
    `tests/api/test_explanation_shape.py`.
- **Amendments:** **A-006** (cost/budget out of p2; recipe-level cost drop
  owned by p3-004) bounds this feature's scope: cost/budget evaluation is not
  part of this contract.

## User-facing behavior

> "User-facing" here means the shape observable by a caller of the
> conversational surface — the client that sends a `/chat` request and consumes
> the SSE stream. This feature defines the shapes; it does not serve them. The
> endpoint that serves them is p3-004's; the web surface that consumes them is
> p3-003's.

- Given a conversational request, the client sends a request carrying a
  **session identifier**, a **message**, and an optional **user context**. This
  contract defines the request's field set and which fields are required.
- The server responds with a **stream of events**, each event being exactly one
  of a fixed vocabulary: `metadata`, `token`, `plan_updated`, `error`, `done`.
  This contract defines the payload shape of each event type and the fields
  each carries. The *transport* (how the stream is opened, framed, and closed)
  is p3-004's; this contract defines only the event payloads.
- The **recommendation**, when one is produced, is exposed at **three levels of
  explanation**:
  - **plan level** — the overall feasibility outcome (a plan was produced, the
    request was infeasible, or the workflow failed), and for an infeasible
    outcome the named binding constraint(s) and, when a plan was produced under
    a permitted relaxation, the relaxed label and applied tolerance;
  - **recipe level** — per-recipe outcome (selected or dropped), and for a
    dropped recipe its drop cause(s);
  - **constraint level** — per-requirement outcome, the resolved food concept,
    the chosen offer (which may be absent when no eligible offer exists), the
    constraint outcome, and any warned conditions.
- A **dropped candidate is always explained**, never silently omitted. The drop
  cause distinguishes **evidence-absent** (the evidence needed to evaluate the
  constraint was missing) from **present-evidence-excludes** (evidence was
  present and ruled the recipe out) from **unmapped** (the requirement could not
  be resolved to a food concept). When multiple causes apply, the contract
  preserves all of them in p2's precedence order
  (`present-evidence-excludes` → `evidence-absent` → `unmapped`).
- The **user payload carries only** the resolved food concept, the chosen
  offer, the per-requirement constraint outcome, and the warned conditions. It
  **never carries** mapping confidence, normalization version, or any source
  identifier (R-16's floor). The SSE contract may additionally exclude other
  audit-only fields (see "Audit-provenance boundary"); the floor is R-16's
  named four categories.
- The **trace is referenced, not embedded.** Every response carries a stable
  **`trace_id`** that correlates the user-visible response with its trace. The
  trace itself is **not** part of any SSE event payload; it is retrievable
  out-of-band by identifier. The retrieval mechanism is not defined by this
  contract (see Clarification C-1).
- A **`plan_updated` event carries both the delta and the three-level
  explanation scoped to the updated meal.** The delta identifies which meal
  changed; the scoped explanation carries the recipe-level outcome and the
  constraint-level outcomes for that meal (including any drop causes), so
  R-17's contract holds for the updated portion (see Clarification C-2).
- An **error** occurring before or during the stream is surfaced as an `error`
  event carrying a stable error code and a human-readable message, consistent
  with the API's standard error envelope. The contract defines the `error`
  event's payload shape; it does not define the endpoint's error-handling
  control flow.
- The contract exposes the **judge/eval integration hooks** a future judge/eval
  layer will consume: the stable `trace_id`, the retrieval guarantee, and the
  structured references the workflow's Generate Response node produced
  (referenced recipe IDs, requirement IDs, drop causes). No judge/eval
  endpoint, storage, or metric is defined here; the hooks exist so a later
  feature can consume them without a contract change.

## Acceptance criteria

- **AC-1** Given the `/chat` request contract, when a request is validated
  against it, then the request carries a session identifier, a message, and an
  optional user context; a request missing the session identifier or the
  message is invalid, and a request omitting user context is valid. (The schema
  is testable by serializing a conforming request and rejecting a request that
  omits a required field.)

- **AC-2** Given the SSE event contract, when any event is validated against it,
  then the event's type is exactly one of `metadata`, `token`, `plan_updated`,
  `error`, `done`, and no other event type conforms. Each event type carries
  the fields this contract defines for it, and an event of a given type missing
  a required field for that type is invalid.

- **AC-2b** Given a `plan_updated` event, when its payload is examined, then it
  carries (a) the delta identifying the changed meal (`day`, `slot`,
  `recipe_id`), and (b) a **three-level explanation scoped to the updated
  meal** carrying the recipe-level outcome and the constraint-level outcomes
  for that meal, including any drop causes. A `plan_updated` event carrying
  only the delta, or only the full-plan explanation, is non-conforming.
  (Clarification C-2.)

- **AC-3** Given a recommendation, when the response is examined, then it
  exposes all three explanation levels — plan, recipe, and constraint — and a
  response missing any one of the three levels is non-conforming.

- **AC-4** Given a recipe that p2 dropped for **absent evidence**, when the
  recipe-level explanation is examined, then the drop cause is reported as
  `evidence-absent`, distinct from `present-evidence-excludes` and from
  `unmapped`.

- **AC-5** Given a recipe that p2 dropped because **present evidence ruled it
  out**, when the recipe-level explanation is examined, then the drop cause is
  reported as `present-evidence-excludes`, distinct from `evidence-absent` and
  from `unmapped`.

- **AC-6** Given a recipe with more than one applicable drop cause, when the
  recipe-level explanation is examined, then all applicable causes are present
  and ordered by p2's precedence (`present-evidence-excludes` →
  `evidence-absent` → `unmapped`); no cause is collapsed or dropped.

- **AC-7** Given a user-facing response payload, when its field set is examined,
  then it contains no `confidence`, no `normalization_version`, and no
  `source_*` / `*_id` provenance field; a payload in which any such field
  appears is non-conforming. **This is R-16's floor** — the named four
  categories. The SSE contract may carry additional exclusions (see AC-7b);
  the R-16 fixture asserts the floor. (R-16, user-payload clause — the named
  fixture `tests/api/test_response_schema.py`.)

- **AC-7b** Given the SSE contract's declared exclusion list, when it is
  examined, then it names the fields the SSE payload excludes in addition to
  R-16's floor (if any). The SSE contract's own tests assert the declared
  exclusions; a field the contract declares excluded that appears in the user
  payload is non-conforming. R-16's floor is the minimum; the SSE contract is
  free to be stricter. (Clarification C-3.)

- **AC-8** Given the execution trace object, when it is examined, then the
  audit-only provenance R-16 names (mapping confidence, normalization version,
  source identifiers) is retained in the trace and reachable there. (R-16,
  trace-side clause — the named fixture `tests/api/test_response_schema.py`.)
  **This assertion is `xfail` while Finding F-P3-1 is unresolved**, because the
  embedded `PlanTraceView` does not yet carry those fields; the `xfail` reason
  references F-P3-1. It is not removed or weakened.

- **AC-9** Given a per-requirement constraint-level explanation, when it is
  examined, then it exposes the resolved food concept, the chosen offer, the
  constraint outcome, and the warned conditions, and nothing beyond R-16's
  allowed user-facing set; the chosen offer may be absent (null) when no
  eligible offer exists, and its absence is not reported as an error or a drop.

- **AC-10** Given a response correlated with its trace, when the stream is
  examined, then a stable **`trace_id`** is present that correlates the
  user-visible response with its trace; the trace itself is **not** part of any
  SSE event payload; and the contract states that the trace is retrievable
  out-of-band by identifier. The retrieval mechanism is not defined by this
  contract. (Clarification C-1; judge/eval hook; R-16 trace boundary.)

- **AC-11a** Given the two constitution-named fixtures, when conformance is
  run, then `tests/api/test_response_schema.py` (R-16) and
  `tests/api/test_explanation_shape.py` (R-17) exist at those paths and assert
  the contracts named in AC-3 through AC-10.

- **AC-11b** Given the R-16 fixture, when it is run, then its **user-payload
  exclusion clause** (AC-7) passes (not `xfail`), and its **trace-side
  retention clause** (AC-8) is `xfail` with a reason referencing F-P3-1. The
  `xfail` is deliberate and is not removed or weakened.

- **AC-12** Given a workflow `failure` outcome, when the response is shaped,
  then the contract surfaces the failure as an `error` event with a stable code
  and a human-readable message, carries no recommendation payload presented as
  complete, and the trace identifier still correlates the response with its
  trace.

- **AC-13** Given an infeasible workflow outcome with named binding
  constraint(s), when the plan-level explanation is examined, then the binding
  constraint(s) are exposed at the plan level and the recipe-level and
  constraint-level explanations (including dropped candidates) are present and
  intact. (R-14's output surfaces unchanged; this feature does not re-decide
  feasibility.)

- **AC-14** Given a plan produced under a permitted nutrient-tolerance
  relaxation, when the plan-level explanation is examined, then it carries the
  relaxed label and the applied tolerance value unchanged from the workflow
  outcome.

## Edge cases & errors

- **Offer absent for a requirement.** The constraint-level explanation shows a
  null chosen offer; this is a valid state, not an error and not a drop (AC-9).
- **Multi-cause drop.** All applicable causes are preserved in p2's precedence
  order; none is collapsed (AC-6).
- **Workflow failure.** Surfaced as an `error` event with a stable code; no
  partial recommendation is presented as complete (AC-12).
- **Infeasible outcome.** The plan level names the binding constraint(s); the
  recipe/constraint levels still render their reasoning (AC-13).
- **Empty eligible pool vs. no assignment.** The plan-level explanation
  preserves the distinction the workflow carries (no recipe survived vs.
  recipes survived but no assignment filled the horizon); this contract does
  not merge the two.
- **Trace-side provenance absent (Finding F-P3-1).** R-16's trace-side clause
  cannot pass until the provenance reaches the trace; the fixture's trace-side
  assertion is `xfail`, not deleted, and the user-payload clause passes
  independently (AC-8, AC-11b).
- **Provenance leak attempt.** Any user-facing field carrying `confidence`,
  `normalization_version`, or a `source_*` / `*_id` value makes the payload
  non-conforming, caught by R-16's fixture (AC-7). Any field the SSE contract
  additionally excludes, if it leaks, is caught by that contract's own tests
  (AC-7b).
- **Unknown or extra SSE event type.** An event whose type is not one of the
  five named types is non-conforming (AC-2).
- **`plan_updated` with delta only, or with full-plan explanation.** Both are
  non-conforming; the contract requires the delta plus the meal-scoped
  explanation (AC-2b).
- **Trace in the SSE payload.** Any SSE event carrying the trace itself is
  non-conforming; the trace is referenced by `trace_id` only (AC-10).
- **Cost/budget statement in a request.** Out of scope for this contract; cost
  surfacing and the recipe-level cost drop are p3-004's (A-006). The contract
  does not define a cost-drop explanation.
- **Partial-coverage data (DQ-1..DQ-7).** The explanation shapes whatever the
  plan produced; the contract neither compensates for nor masks coverage gaps.

## Non-goals

- **Implementing the `/chat` endpoint or the SSE transport mechanism.** p3-004
  owns the endpoint implementation and the stream's opening, framing, and
  closing; p3-002 defines the request and event *schemas* only.
- **Implementing the workflow nodes.** p3-001 owns Extract Constraints, Plan,
  and Generate Response; p3-002 consumes the `TraceEnvelope` they produce.
- **The web planner experience (p3-003).** A separate frontend effort consumes
  p3-002's response shape; p3-002 does not build it.
- **The judge/eval layer's implementation.** p3-002 exposes the integration
  hooks (`trace_id`, retrieval guarantee, structured references); the judge
  itself — its endpoints, storage, and metrics — is a later feature. **No
  judge/eval API surface is planned in the current roadmap.**
- **Trace retrieval endpoint.** The contract guarantees a stable `trace_id`
  and retrievability; the endpoint or mechanism that serves the trace is not
  defined by this contract (see Clarification C-1).
- **Cost and budget evaluation.** Owned by p3-004 per A-006; this contract
  defines no cost-drop explanation and no budget surfacing.
- **Re-deciding p2's reasoning.** The three-level outcomes, the drop causes,
  and their precedence pass through unchanged; this feature shapes them for the
  user, it does not recompute them.
- **Fixing Finding F-P3-1 or the data-coverage findings (DQ-1..DQ-7).** The
  trace-side provenance gap is owned upstream; this contract tracks it via the
  `xfail` and does not resolve it.
- **R-16 rule-text amendment to widen the exclusion list beyond its named four
  categories.** R-16's named four are the floor (Clarification C-3). If a
  broader constitutional list is wanted, it requires an amendment; p3-002 does
  not initiate it.
- **Choosing the contract's concrete data structures, field names, module
  layout, serialization library, or test internals.** Those are plan-stage
  decisions; this spec names the shapes and the required fields, not their
  implementation.

## Interfaces & dependencies

### Endpoint-to-feature mapping (define vs. implement)

| Surface / endpoint | Owner | p3-002's relationship |
|---|---|---|
| `/chat` request schema | **p3-002 defines** | the request field set and required fields |
| SSE event schemas (`metadata`, `token`, `plan_updated`, `error`, `done`) | **p3-002 defines** | the payload shape of each event type, including `plan_updated`'s delta + scoped explanation |
| Three-level explanation shape (plan / recipe / constraint) | **p3-002 defines** | the user-facing explanation contract |
| Audit-provenance boundary (R-16 floor + SSE-specific exclusions) | **p3-002 defines** | what the user sees vs. what the trace retains |
| Trace identifier and retrieval guarantee | **p3-002 defines** | stable `trace_id`; retrievability out-of-band; mechanism not defined here |
| R-16 fixture `tests/api/test_response_schema.py` | **p3-002 creates** | both clauses (user-payload exclusion + trace-side retention) |
| R-17 fixture `tests/api/test_explanation_shape.py` | **p3-002 creates** | three levels present + distinct drop causes |
| Judge/eval integration hooks | **p3-002 defines** | `trace_id`, retrieval guarantee, structured references |
| `POST /api/v1/chat` endpoint + SSE transport | p3-004 implements | p3-004 implements p3-002's schemas |
| Trace retrieval endpoint | not assigned | p3-002 guarantees retrievability; the endpoint is not defined here |
| Workflow nodes + `TraceEnvelope` production | p3-001 implements | p3-002 consumes the envelope |
| Web request/response surface for the planner UI | p3-003 (separate effort) | p3-003 consumes p3-002's response shape |
| Cost/budget surfacing + recipe-level cost drop | p3-004 (per A-006) | out of p3-002's scope |

### Input contract

- p3-002's input is p3-001's **`TraceEnvelope`** (constitution-compliant,
  versioned): a schema version; the workflow `Outcome`
  (`plan | infeasible | failure`); the raw message; the parsed constraint set;
  the unapplied constraints; one record per node run; one record per LLM
  invocation; and the embedded **`PlanTraceView`**.
- Through the embedded `PlanTraceView`, p3-002 reaches the feasibility outcome
  and reason, the binding constraints, the applied tolerance, the per-recipe
  outcomes (with drop causes), and the per-requirement outcomes (resolved
  concept, selected offer, warnings). These are the three levels of explanation
  p3-002 shapes for the user.
- The drop causes p3-002 surfaces (`evidence-absent`,
  `present-evidence-excludes`, `unmapped`) and their precedence are p2's
  (p2-001, p2-003); p3-002 does not define new causes.

### Output contract

- The **`/chat` request schema**: a session identifier, a message, and an
  optional user context, with the session identifier and message required.
- The **five SSE event schemas**: `metadata`, `token`, `plan_updated`, `error`,
  `done`, each with the field set this contract defines; the event type is
  exactly one of the five. The `plan_updated` event carries the delta for the
  changed meal **and** the three-level explanation scoped to that meal
  (recipe-level outcome, constraint-level outcomes, drop causes).
- The **three-level explanation shape**: plan / recipe / constraint, with
  dropped candidates and distinct drop causes at the recipe level.
- The **audit-provenance boundary**: the user payload exposes only the resolved
  food concept, chosen offer, per-requirement constraint outcome, and warned
  conditions; `confidence`, `normalization_version`, and `source_*` / `*_id`
  provenance are excluded from the user payload (R-16's floor). The SSE
  contract declares any additional exclusions of its own (endpoint-specific
  floor above R-16); prices are **not** excluded by R-16 and are allowed in the
  user payload unless the SSE contract declares otherwise for product reasons.
- The **trace identifier and retrieval guarantee**: a stable `trace_id` is
  present in the response; the trace is not embedded in any SSE event; the
  trace is retrievable out-of-band by identifier. The retrieval mechanism is
  not defined by this contract.
- The precise field layout, field names, and data structures are **not** fixed
  here; they are plan-stage decisions. This spec names the required fields and
  the shapes, not their concrete representation.

### Audit-provenance boundary

- R-16's named four categories — `confidence`, `normalization_version`,
  `source_*`, `*_id` — are the **floor**. They are excluded from the user
  payload in every response.
- The SSE contract may declare **additional exclusions** (endpoint-specific).
  If it does, the SSE contract's own tests assert them. The calculator
  endpoint's exclusion list (`food_key`, `fdc_id`, `mapping_version`,
  `nutrition_rank`, `selection_priority`, `approval_status`) remains its own;
  it is stricter than R-16's floor and is not part of this contract.
- **Prices are not excluded by R-16.** If the SSE contract surfaces a price
  (e.g., the `plan_updated` delta's `cost_sgd` in the API doc), it is in the
  user payload by design. Excluding prices is a product decision the SSE
  contract may take; if taken, it is recorded as an additional exclusion in
  AC-7b.

### Trace boundary

- The trace is **referenced by `trace_id`**, not embedded in the SSE stream
  (Clarification C-1). The trace is retrievable out-of-band by identifier.
- The audit-only provenance R-16 names is retained **in the trace**. Its
  presence there is subject to **Finding F-P3-1**: the embedded `PlanTraceView`
  does not currently carry mapping confidence, normalization version, or source
  identifiers, so R-16's trace-side clause is not satisfiable through the
  p3-001 trace until F-P3-1 resolves.

### Fixtures

- `tests/api/test_response_schema.py` (R-16) and
  `tests/api/test_explanation_shape.py` (R-17) are **created by this feature at
  the constitution's named paths**. Neither exists in the codebase today.
- The **R-16 fixture asserts both clauses**: user-payload exclusion of
  `confidence` / `normalization_version` / `source_*` / `*_id` (passing), and
  trace-side retention of that provenance (`xfail` under F-P3-1). The two
  clauses' verdicts are visible independently (AC-11a, AC-11b).
- The **R-17 fixture** builds two responses — one where a recipe is dropped for
  absent evidence, one where it is dropped for present-but-excluding evidence —
  and asserts each carries the distinct cause and that all three explanation
  levels are present in both.
- The R-16 fixture mirrors the user-payload exclusion list R-16 names (the
  four categories). The calculator's `tests/features/calculator/test_response_schema.py`
  asserts a broader list (its own endpoint-specific exclusions); it is not
  R-16's fixture and is not superseded by it. The constitution names
  `tests/api/test_response_schema.py`; the divergence from the calculator
  test's location is p2-002's **F-D**, also carried as p3-001's **BD-2a**,
  tracked for phase review. R-17's named fixture was absent (p3-001's
  **BD-2b**); p3-002 is its assigned owner.

### Dependency (Finding F-P3-1)

- R-16's trace-side clause requires `confidence`, `source_snapshot_id`
  (source identifier), and `mapping_version` (normalization/mapping version) to
  reach the trace via the offer reference and `PlanTrace`. The resolution is a
  **p2-002 reopen** (extend the offer reference to carry the provenance) plus a
  **p2-003 propagation** (carry it onto `PlanTrace`'s recipe and requirement
  outcomes).
- If that reopen has not landed when p3-002's R-16 fixture is written, the
  trace-side clause is **`xfail`** with a reason referencing F-P3-1; the
  user-payload clause passes regardless.
- **Owner:** F-P3-1 is owned by p2-003 (per p3-001's D-1). The reopen path
  crosses p2-002 and p2-003; both route through their own spec owners. p3-002
  does not perform the reopen.

### Judge/eval integration hooks

- The response stream exposes the fields a future judge/eval layer will need:
  a stable **`trace_id`** correlating the response with its trace; a
  **retrieval guarantee** for the trace by identifier; and the **Generate
  Response node's structured references** (referenced recipe IDs, requirement
  IDs, drop causes), which p3-001 already produces for its deterministic check.
- **No judge/eval API surface is planned in the current roadmap.** p3-002
  defines the hooks so a later feature can consume them without a contract
  change; it does not define endpoints, storage, or metrics.

### Downstream dependencies

- **p3-004** implements the `/chat` endpoint and SSE transport against this
  contract and owns cost/budget surfacing on follow-up turns.
- **p3-003** (separate effort) consumes this contract's response shape for the
  web planner UI.

### Runtime / data dependency

- The plan path reads the canonical graph, subject to the tracked
  `data-prep-price-path` finding and DQ-1..DQ-7. Conformance evidence uses the
  phase's approved fixtures; the contract shapes whatever the plan produces.

## Open questions

None blocking. All three original blocking questions (trace embedding,
`plan_updated` payload, R-16 exclusion list) are resolved and recorded under
`## Clarifications`.

## Clarifications

- **C-1 (trace: referenced, not embedded, 2026-10-17, human).** The trace does
  not travel in the SSE stream. Every response carries a stable `trace_id`
  that correlates the user-visible response with its trace; the trace itself
  is retrievable **out-of-band** by identifier. The retrieval mechanism (an
  endpoint, a privileged channel, or a separate service) is **not defined by
  this contract**; the contract guarantees only that a stable identifier is
  present and that the trace is retrievable by it. Rationale: R-16's
  user-payload / trace boundary stays clean at the transport layer; the trace
  envelope is large and not every client needs it; the SSE contract's version
  is decoupled from the trace envelope's version. **Consequential — flag for
  `decisions.md` at close.**
- **C-2 (`plan_updated`: delta + scoped three-level explanation, 2026-10-17,
  human).** A `plan_updated` event carries (a) the delta identifying the
  changed meal (`day`, `slot`, `recipe_id`) and (b) the three-level
  explanation **scoped to that meal** — the recipe-level outcome and the
  constraint-level outcomes (including any drop causes) for the updated meal.
  It does not carry the full-plan explanation (the plan level is unchanged by
  an incremental update). Rationale: R-17's contract requires three levels of
  explanation for every recommendation; the updated meal is a recommendation,
  so it must be explained at the recipe and constraint levels; scoping keeps
  the payload incremental. **Consequential — flag for `decisions.md` at
  close.**
- **C-3 (R-16 exclusion list: layered — R-16 is the floor, endpoints may be
  stricter, 2026-10-17, human).** R-16's named four categories (`confidence`,
  `normalization_version`, `source_*`, `*_id`) are the **floor**; the R-16
  fixture asserts those. Each endpoint may declare additional exclusions of
  its own above the floor; if it does, its own tests assert them. The
  calculator endpoint's exclusion list (which additionally excludes `food_key`,
  `fdc_id`, `mapping_version`, `nutrition_rank`, `selection_priority`,
  `approval_status`) remains its own endpoint-specific list, not part of R-16's
  floor. **Prices are not excluded by R-16**; they are user-meaningful in a
  cost-aware response and are allowed in the user payload unless the SSE
  contract declares a product-reason exclusion. Rationale: R-16's rule text
  names four categories; extending it beyond those requires a rule amendment,
  which is out of p3-002's scope. The layered reading preserves the rule's
  literal contract while allowing endpoints to be stricter where their payload
  carries additional audit-only fields. **Consequential — flag for
  `decisions.md` at close.**
