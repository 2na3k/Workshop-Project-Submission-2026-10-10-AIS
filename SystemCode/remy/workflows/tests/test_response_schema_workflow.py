"""Workflow R-16 mirror of the constitution's tests/api/test_response_schema.py.

The current API authority is
api/tests/features/calculator/test_response_schema.py::test_user_payload_field_set;
the path divergence is tracked for phase review in plan BD-2.
"""

from dataclasses import asdict

from workflows.graph import build
from workflows.models import PlanResult, PlanTraceView


USER_PAYLOAD_EXCLUSIONS = (
    "confidence",
    "food_key",
    "fdc_id",
    "source_",
    "normalization_version",
    "mapping_version",
    "nutrition_rank",
    "selection_priority",
    "approval_status",
)


class _LLM:
    provider = "fake"
    model = "fake"

    def __init__(self, response):
        self.response = response

    def invoke(self, prompt):
        return self.response


def _workflow():
    class _Port:
        def generate(self, request):
            return PlanResult("plan-1", "complete", "ok"), PlanTraceView("feasible", None)

    return build(
        extract_llm=_LLM({"horizon_days": 1, "meals_per_day": 1}),
        plan_port=_Port(),
        response_llm=_LLM({"text": "Plan is ready.", "recipe_ids": [], "requirement_ids": [], "drop_causes": []}),
    ).invoke({"raw_message": "Plan one day"})


def test_user_payload_excludes_provenance():
    state = _workflow()
    payload = asdict(state["outcome"])

    def keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                yield from keys(nested)

    all_keys = set(keys(payload))
    assert not any(
        key == excluded or key.startswith(excluded)
        for key in all_keys
        for excluded in USER_PAYLOAD_EXCLUSIONS
    )
    assert state["outcome"].text.startswith("Plan is ready.")


# def test_trace_side_provenance_is_deferred_to_f_p3_1():
#     pytest.xfail("F-P3-1: PlanTrace does not carry R-16 provenance fields")
#     assert False
