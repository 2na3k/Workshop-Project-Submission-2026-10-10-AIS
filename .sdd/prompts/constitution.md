# Prompt — Constitution

## Input
- proposal.md
- constitution template (`templates/constitution.md`)
- AGENTS.md
- source material listed in the proposal's Source material section
- system design docs, tech stack docs, database design docs
- backend docs: API rules, project structure

## Output
- docs/sdd/constitution.md (once per project, or per approved amendment)

## Category guidance
Use categories that reflect this project's own structure. Derive them from the
proposal's Behavioral Rules and the two or three biggest cross-cutting
commitments. Do not use generic categories ("Stack", "Security") unless they
genuinely fit.

## Source precedence
The inputs are ordered by authority:
proposal > Resolved Questions > Behavioral Rules > system design docs >
tech stack docs > API rules / project structure docs

When two sources disagree, the higher-authority one wins. Record the conflict in
the rule's `Why:` field. Never average them. Never support two schemas at once.

## Rule authoring
Every rule needs Rule / Why / Check.
- A `Why:` without a citation (goal, Resolved Question, external constraint, or
  Behavioral Rule) is a preference, not a rule.
- A rule without a `Check:` is not enforceable. The Check is one of:
    * a CI command (import-linter, schema tests, ruff)
    * a named reviewer pattern (what to look for in a diff)
    * a named test fixture (the assertion it makes)
- Drop any rule you cannot check.

## Rule count
Aim for 8–15 rules. More than 20 means you are writing a spec, not a constitution.
Fewer than 5 means the proposal is under-specified — route back to the proposal
stage rather than inventing rules.

## Numbering
Number R-1..R-N monotonically across all categories. Downstream artifacts cite rule
IDs; renumbering is a breaking change and requires an amendment.

## Process
1. Confirm the gate passes (`sdd.py gate constitution <project>`).
2. Confirm all open questions in proposal.md are resolved. A rule that requires an
   unmade decision is not a rule.
3. Derive categories and write rules.
4. Ask the human to approve or amend.
5. On approval: set `Status: approved` and `Version`. On an amendment: increment
   `Version`, mark the amendment file `approved`.

## Do not
- Encode feature-specific detail.
- Add a rule the proposal does not imply.
- Add a rule with no Check.
- Resolve a source conflict by averaging — cite the higher-authority source.
- Maintain a changelog inside constitution.md.
- Renumber rules without an amendment.
