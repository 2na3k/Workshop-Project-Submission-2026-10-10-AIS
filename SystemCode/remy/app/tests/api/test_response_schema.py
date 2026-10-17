from dataclasses import asdict

import pytest

from app.chat_contract import CHAT_FORBIDDEN_FIELDS, from_trace_envelope
from workflows.models import Outcome, PlanTraceView, RecipeOutcomeView, RequirementOutcomeView
from workflows.trace import assemble_trace


def _representative_trace():
    plan_trace = PlanTraceView(
        feasibility_outcome="feasible",
        reason=None,
        recipes=(RecipeOutcomeView("recipe-1", "selected"),),
        requirements=(
            RequirementOutcomeView(
                recipe_id="recipe-1",
                requirement_id="requirement-1",
                constraint="vegan",
                state="satisfied",
                requirement_text="tofu",
                resolved_concept="tofu",
                selected_offer={"listing_name": "Firm tofu", "retailer": "Market"},
                confidence=0.95,
                source_snapshot_id="snapshot-1",
                mapping_version="v1.0",
                warnings=()
            ),
        ),
    )
    return assemble_trace(
        raw_message="Plan a vegan meal",
        parsed_constraints=None,
        unapplied_constraints=(),
        outcome=Outcome(kind="plan"),
        plan_trace=plan_trace,
    )


def _keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _keys(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _keys(nested)


def test_user_payload_excludes_audit_provenance():
    payload = from_trace_envelope(_representative_trace(), trace_id="trace-1").model_dump()
    keys = list(_keys(payload))
    assert not [key for key in keys if any(field in key for field in CHAT_FORBIDDEN_FIELDS)]


# @pytest.mark.xfail(strict=True, reason="F-P3-1: PlanTraceView carries no R-16 audit provenance; owned by p2-003")
def test_trace_retains_audit_provenance():
    trace = _representative_trace()
    trace_fields = list(_keys(asdict(trace.plan_trace)))
    assert {"confidence", "mapping_version", "source_snapshot_id"}.issubset(trace_fields)
