### Prompt for implementation agent — continue p3-004

**Human decision:** Option 1. Leave `PlanUpdatedEvent` construction in `chat_router.py` **exactly as it currently runs** — do not edit it, do not pass `None`, do not touch `chat_contract.py`. R-17 three-level explanation is delivered via the non-streaming `ChatResponseEnvelope`, not via SSE frames.

**Context established:**

- Step 1: the 7 workflow test failures pre-existed BD-6 (recorded in plan `## Revision notes` line 411). Do not fix them; they are out of scope.
- Step 2: `PlanUpdatedEvent.explanation` is `required: MealScopedExplanation`. Leave as-is.
- BD-6 code changes are landed (async handler, status tokens, timing, `_explanation_lines` removal, `num_predict=400`). `lint-imports` 4/0.

Continue with Steps 3–6, then commit if gates hold.

---

### Step 3 — repurpose the three-levels test

**File:** `SystemCode/remy/app/tests/api/test_chat_endpoint.py`

Find `test_three_levels_present_in_stream`. Rename to `test_three_levels_present_in_envelope`. Repurpose:

- Drive the non-streaming path directly. Build a `TraceEnvelope` (reuse any existing fixture that produces one; the same `TraceEnvelope` the workflow produces) → call `from_trace_envelope(envelope, trace_id)` from `app.chat_contract` → assert the returned `ChatResponseEnvelope` contains plan-level, recipe-level, and constraint-level explanations.
- Do **not** route through `/chat`.
- Add the comment: `# BD-6: three-level explanation is delivered via ChatResponseEnvelope, not SSE frames; PlanUpdatedEvent.explanation is required and meal-scoped only.`
- Keep the AC-13 reference in the docstring.

**Done when:** `pytest SystemCode/remy/app/tests/api/test_chat_endpoint.py::test_three_levels_present_in_envelope -q` passes.

---

### Step 4 — fix remaining app test failures

Run:

```bash
pytest SystemCode/remy/app/tests/api -q --tb=short -rf
```

Classify each failure:

- **Kind 1 — stale stream-shape assertion.** Test asserts behavior that only held before `_explanation_lines` was removed from tokens, or asserts exact token counts. **Fix:** update the assertion to the new shape (`metadata` + 2 status tokens + N prose tokens + `plan_updated` delta + `done`). If the test asserted `recipe_id` in token text, move that assertion to `plan_updated.delta`.
- **Kind 2 — cost-projection fixture with empty scoped ingredients.** In `test_cost_projection.py`, the request message produces empty `_scoped_ingredients`. **Fix:** change the message to name an ingredient that exists in the plan (e.g. `"how much does milk chocolate cost?"`). Do not touch the cost branch — empty scoped correctly means "no cost, no error" per the spec edge case.
- **Kind 3 — other.** Report the failing test name and one-line traceback in your status. Do not fix without instruction.

Apply Kind 1 and Kind 2. Re-run:

```bash
pytest SystemCode/remy/app/tests/api -q --tb=short -rf
```

**Done when:** 0 failures, or only Kind 3 failures remain and are named in your status.

---

### Step 5 — manual `/chat` check

Terminal 1 (from `SystemCode/remy`):

```bash
uvicorn app.main:app --port 8000
```

Terminal 2:

```bash
time curl -N -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","message":"cheap high-protein dinner under $5 for 2 days"}' \
  | tee /tmp/chat.log
```

Capture and paste **all five**:

1. **First-frame latency.** Time to first `event: metadata` line — should be ~<1s. If your terminal cannot show timestamps, use:
   ```bash
   awk '/^event:/{print systime()": "$0; exit}' /tmp/chat.log
   ```
   or note "observed visually at ~Xs".

2. **Token counts.** Number of `token` frames before the first prose block. Expect exactly **2** status tokens (`"Planning your meals…"`, `"Generating your recommendation…"`), then N prose. Command:
   ```bash
   grep -c '^event: token' /tmp/chat.log
   ```

3. **Full user-facing text.** Command:
   ```bash
   grep '^data:' /tmp/chat.log | sed 's/^data: //' | jq -r 'select(.text) | .text' 2>/dev/null
   ```
   Paste the entire output.

4. **Audit leakage check.** Command:
   ```bash
   grep '^data:' /tmp/chat.log | sed 's/^data: //' | jq -r 'select(.text) | .text' 2>/dev/null \
     | grep -c 'recipe_id' || true
   ```
   Expect `0`. If >0, `_explanation_lines` removal did not take — clear `__pycache__`, restart uvicorn, retry.

5. **LLM latencies.** The `latency` values from `envelope.llm_invocations` (extract primary, extract retry if fired, generate). If the trace is embedded in the stream:
   ```bash
   grep -o '"latency": [0-9.]*' /tmp/chat.log | head -5
   ```
   Report each value; expect ~3–15s for extract, ~30–90s for generate.

**Done when:** all five values are in your status.

---

### Step 6 — final counts

```bash
uv run lint-imports
pytest SystemCode/remy/app/tests/api -q --tb=no
pytest SystemCode/remy/workflows/tests -q --tb=no
```

Report exact pass/fail counts. Expected:

- `lint-imports`: 4 kept, 0 broken.
- App tests: 0 failed (after Step 3+4).
- Workflow tests: 7 failed, 23 passed (pre-existing per Step 1).

---

### Step 7 — commit if all gates hold

Commit only if:

- Step 3 repurposed test passes.
- Step 4 app tests have 0 failures (or only named Kind 3 failures).
- Step 5 manual check produced all five values.
- Step 6 `lint-imports` 4/0.
- Workflow failures still 7 (pre-existing; not fixed here).

If any gate fails, **do not commit**. Report the failing gate and stop.

**Commit message:**

```
fix(p3-004): real SSE framing, real latencies, no audit dump (BD-6)

- chat_router: async def chat -> async def _stream_chat; two status tokens
  emitted before the blocking workflow.invoke
- chat_router: _explanation_lines removed from token stream
- nodes: time.perf_counter around extract/generate invokes; LLMInvocation.latency
- tests: stream-shape assertions updated; test_three_levels_present_in_envelope
  repurposed against the non-streaming projection
- plan: BD-6 and BD-6 remainder recorded; 7 pre-existing workflow test failures
  tracked as out of scope

Option 1 taken: PlanUpdatedEvent.explanation left as required/meal-scoped;
R-17 three-level explanation delivered via ChatResponseEnvelope.
```

---

### Step 8 — extend BD-6 remainder

Append (do not edit the existing BD-6 entry):

```markdown
- **BD-6 (remainder, verified)** — Option 1 taken. `PlanUpdatedEvent.explanation`
  is required and typed `MealScopedExplanation`; left as-is. R-17 three-level
  explanation is delivered via the non-streaming `ChatResponseEnvelope`
  (`from_trace_envelope`), asserted by `test_three_levels_present_in_envelope`.
  SSE stream: `metadata` + two status `token`s (`"Planning your meals…"`,
  `"Generating your recommendation…"`) + N prose `token`s + `plan_updated`
  (delta only) + `done`. Seven pre-existing workflow test failures tracked as
  out of scope (confirmed by `git stash` on BD-6 changes; same 7 fail without
  the pass). Manual check: first-frame latency = <Xs>, token counts = <2 status
  + N prose>, full text = <chars / short>, audit leakage in text = <0>, LLM
  latencies = <extract, generate>.
```

---

### Status format to return

```
STEP 3 (repurposed test): <pass/fail>
STEP 4 (app tests): <N failed>, Kind 3 = <list or none>
STEP 5 (manual):
  first-frame latency = <s>
  token counts = <2 status + N prose>
  full text (paste):
  ---
  <full text>
  ---
  audit leakage in text = <count>
  LLM latencies = <extract>, <generate>
STEP 6 (final): lint-imports = <kept/broken>; app tests = <pass/fail>; workflow tests = <pass/fail>
STEP 7 (commit): <done | blocked on X>
```

---

### One-liner

Option 1 locked in. Hand the agent the prompt above — it does Steps 3–6 (repurpose one test, fix 2–5 stale/fixture tests, run manual `curl -N`, capture counts) and commits in ~30–40 minutes if the manual check shows `metadata` arriving in under a second and short text with no `recipe_id` in it. If the manual check shows a 30-second silence before the first frame, the async generator isn't being driven — stop and report.
