---
name: sdd-constitution
description: Author or amend the project constitution in the SDD flow. Use once per project, or whenever an approved amendment changes a binding rule. Produces checkable rules from the proposal and existing architecture. Never encodes feature-specific detail.
---

# sdd-constitution

## Inputs
`proposal.md`, `AGENTS.md`, source material, existing architecture, research. On an amendment, the
approved `amendments/A-*.md` and the current `constitution.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate constitution <project>` must pass. Otherwise stop.
2. Extract the durable constraints implied by the proposal and the existing system.
3. Group them under categories (stack/architecture, security/data, process…).
4. Write each as Rule / Why / Check. Drop any rule you cannot check.
5. Ask the human to approve or amend.
6. On approval, set `Status: approved`, set `Version`, and on an amendment increment it.

## Do not
- Encode feature-specific detail.
- Add a rule the proposal does not imply.
- Add a rule with no Check.
- Maintain a changelog inside `constitution.md` — `amendments/` is the changelog.
