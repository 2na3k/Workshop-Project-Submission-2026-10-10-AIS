# Prompt — Roadmap + Phases

Input:  proposal.md, constitution.md, AGENTS.md, existing project state.
Output: docs/sdd/roadmap.md, docs/sdd/roadmap-log.md (append-only).

Map every goal to the phase that delivers it. Phases are ordered by dependency
and by risk. Each phase has an Outcome, Goals served, Features, and verifiable
Exit criteria.

Features are named `<phase>-<nnn>-<slug>`. Keep each feature inside one working
context.

Append a roadmap-log entry for every change — phases added, reordered, retired —
with the reason.
