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


def test_real_plan_service_tuple_maps_through_adapter_with_mocked_neo4j():
    from api.features.calculator.models import OfferRef, RecipeNutritionSignal, RequirementOffer
    from api.features.plan.repository import PlanRepository
    from api.features.plan.schemas import PlanRequest
    from api.features.plan.service import PlanService
    from app.plan_adapter import PlanServiceAdapter
    from workflows.models import PlanInput

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def run(self, query, **params):
            return [
                {
                    "recipe_id": "recipe-1",
                    "title": "Pepper recipe",
                    "ingredients": [{
                        "quantity": 10,
                        "unit": "g",
                        "occurrence_id": "ingredient-1",
                        "canonical_key": "black_pepper",
                        "concept_name": "Black pepper",
                        "best_food_key": "food-best",
                        "cleaned_text": "10 g black pepper",
                        "energy_kcal": 10,
                        "nutrition_basis": "per 100 g",
                    }],
                }
            ]

    class Driver:
        def session(self):
            return Session()

    class Calculator:
        def inspect_candidates(self, recipes, servings):
            return {
                recipe.recipe_id: RecipeNutritionSignal(
                    recipe_id=recipe.recipe_id,
                    missing_nutrients=[],
                    selected_offers=[RequirementOffer(
                        occurrence_id="ingredient-1",
                        canonical_key="black_pepper",
                        selected_offer=OfferRef(
                            food_key="food-audit-only",
                            listing_name="Pepper offer",
                            retailer="Example Market",
                        ),
                    )],
                )
                for recipe in recipes
            }

    service = PlanService(PlanRepository(Driver()), calculator_service=Calculator())
    adapter = PlanServiceAdapter(service)
    result, trace = adapter.generate(PlanInput(1, 1))
    assert result.status == "complete"
    assert result.constraint_outcomes[0].requirement_id == "ingredient-1"
    assert trace.requirements[0].requirement_id == "ingredient-1"

    # Guard the API service's actual tuple return shape as well as the adapter.
    direct = service.generate(PlanRequest(horizon_days=1, meals_per_day=1))
    assert isinstance(direct, tuple) and len(direct) == 2
