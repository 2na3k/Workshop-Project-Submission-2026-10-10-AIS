def test_adapter_contract_requires_tuple_return():
    from app.plan_adapter import PlanServiceAdapter
    from workflows.models import PlanInput

    class BrokenService:
        def generate(self, request):
            return object()

    try:
        PlanServiceAdapter(BrokenService()).generate(PlanInput(1, 1))
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("generate did not return a tuple; P-1 prerequisite missing")
