# Prompt — Constitution

## Input:  
proposal.md, AGENTS.md, source material, existing architecture, research.

# Output: docs/sdd/constitution.md (once per project, or per major amendment).

Derive binding, checkable rules from the proposal and the existing architecture.
Each rule needs Rule / Why / Check. A rule without a Check is not a rule.
Prefer few strong rules over many weak ones.

Do not invent constraints the proposal does not imply. Where the proposal is
silent and the choice is consequential, ask the human before writing the rule.

The constitution is long-lived and reused by every feature. Do not encode
feature-specific detail in it.
