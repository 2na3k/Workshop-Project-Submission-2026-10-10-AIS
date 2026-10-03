# Prompt — Close

Input:  approved implementation, review.md, spec clarifications, state.json.
Output: decisions.md, CHANGELOG.md, state.json (updated).

Write decisions.md: plan deviations, consequential clarifications (with date and
who), overrides.
Append a CHANGELOG entry: feature id + name + date, what changed, ACs covered,
link to decisions.md, breaking changes.
Update state.json: status `closed`, review_verdict, updated_at.

Do not edit spec.md, plan.md, or review.md at close.
