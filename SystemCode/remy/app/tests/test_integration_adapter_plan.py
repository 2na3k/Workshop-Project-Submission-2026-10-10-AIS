def test_adapter_contract_requires_tuple_return():
    from app.plan_adapter import PlanServiceAdapter

    class BrokenService:
        def generate(self, request):
            return object()

    try:
        PlanServiceAdapter(BrokenService()).generate(None)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("generate did not return a tuple; P-1 prerequisite missing")
