---
name: sdd-constitution
description: Author or amend the project constitution in the SDD flow. Use once per project, or whenever an approved amendment changes a binding rule. Produces checkable rules from the proposal and existing architecture. Never encodes feature-specific detail.
---

# sdd-constitution

## Inputs
`proposal.md`, `AGENTS.md`, source material, existing architecture and stack docs.
Template: `.sdd/templates/constitution.md`.
On an amendment: the approved `amendments/A-*.md` and the current `constitution.md`.

## Procedure
1. Initial pass: `python .sdd/scripts/sdd.py gate constitution <project>` must pass.
   Amendment pass: the amendment file must exist, be marked `approved`, and cite
   its trigger.
2. Confirm all open questions in `proposal.md` are resolved. A rule that requires
   an unmade decision is not a rule — route it back to the proposal stage.
3. Derive categories from the proposal's Behavioral Rules and the project's
   cross-cutting commitments. Do not use generic categories.
4. Write each rule as Rule / Why / Check. The Why cites the proposal goal,
   Resolved Question, or Behavioral Rule. The Check is a CI command, a named
   reviewer pattern, or a named test fixture. Drop any rule you cannot check.
5. Aim for 8–15 rules. Number R-1..R-N monotonically across categories.
6. Ask the human to approve or amend.
7. On approval: set `Status: approved`, set `Version`. On an amendment: increment
   `Version`, mark the amendment file `approved`.

## Do not
- Encode feature-specific detail.
- Add a rule the proposal does not imply.
- Add a rule with no Check.
- Resolve a conflict between sources by averaging — cite the higher-authority
  source (proposal > Resolved Questions > Behavioral Rules > design docs >
  stack docs > API/structure docs).
- Renumber rules without an amendment.
- Maintain a changelog inside `constitution.md`.
