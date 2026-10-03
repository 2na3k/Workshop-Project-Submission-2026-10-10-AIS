# Prompt — Clarify

Input:  spec.md (with open questions), AGENTS.md, human answers.
Output: updated spec.md (in place). No separate artifact.

Resolve blocking open questions with the human. Log **every** resolution in
`## Clarifications` with the answer, date, and who answered. Check off the
matching open question.

A clarification is *consequential* if it changes scope, contradicts the
constitution, or affects other features. Consequential clarifications are also
recorded in `decisions.md` at Close — but they are still logged in spec.md
either way. Never omit a clarification from spec.md.

Clarify is mandatory before Plan for any feature touching a rule flagged in the
constitution as high-risk.
