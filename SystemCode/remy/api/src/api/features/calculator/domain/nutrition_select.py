"""Deterministic per-nutrient selection from accepted food candidates."""

from ..models import FoodFacts


def select_nutrient_value(
    candidates: list[FoodFacts], field: str
) -> tuple[float | None, FoodFacts | None]:
    """Return the winning non-null value and its accepted candidate."""
    usable = [
        candidate for candidate in candidates
        if candidate.approval_status == "accepted"
        and getattr(candidate.nutrients, field, None) is not None
    ]
    if not usable:
        return None, None

    def key(candidate: FoodFacts) -> tuple:
        rank = candidate.nutrition_rank
        priority = candidate.selection_priority
        return (
            0 if candidate.source_kind == "crawler_fdc_profile" else 1,
            rank is None, rank if rank is not None else 0,
            priority is None, priority if priority is not None else 0,
            candidate.food_key is None, candidate.food_key or "",
        )

    winner = min(usable, key=key)
    return getattr(winner.nutrients, field), winner
