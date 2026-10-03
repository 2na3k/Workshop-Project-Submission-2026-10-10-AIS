# Prompt — Amendment

Input:  phase review, retro, or a finding routed to `constitution`.
Output: docs/sdd/amendments/A-YYYY-MM-DD-<slug>.md (+ updated constitution.md on approval).
Role:   constitution agent proposes, human approves.

Fill Trigger, Current rule, Proposed change (exact text), Why (with evidence from
the trigger), Impact.

On approval: edit constitution.md in place, increment its version, mark the
amendment `approved`. The amendment file is the record of the change and is never
deleted. constitution.md keeps no changelog of its own.
