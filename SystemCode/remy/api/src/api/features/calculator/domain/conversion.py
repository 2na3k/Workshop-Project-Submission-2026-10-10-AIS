import math
from api.core.exceptions import AppError
from ..exceptions import MissingUnitConversion


def to_grams(quantity: float, unit: str, grams_per_tbsp: float | None = None,
             grams_per_piece: float | None = None) -> tuple[float, list[str]]:
    if unit in ("g", "ml"):
        grams = quantity
        warnings = ["ML_ASSUMED_GRAMS"] if unit == "ml" else []
    elif unit == "kg":
        grams, warnings = quantity * 1000.0, []
    elif unit == "tbsp":
        if grams_per_tbsp is None or not math.isfinite(grams_per_tbsp) or grams_per_tbsp <= 0:
            raise MissingUnitConversion("No positive grams_per_tbsp conversion is available")
        grams, warnings = quantity * grams_per_tbsp, []
    elif unit == "pc":
        if grams_per_piece is None or not math.isfinite(grams_per_piece) or grams_per_piece <= 0:
            raise MissingUnitConversion("No positive grams_per_piece conversion is available")
        grams, warnings = quantity * grams_per_piece, []
    else:
        raise AppError(f"Unsupported unit: {unit}")
    if not math.isfinite(grams) or grams <= 0:
        raise AppError("Converted mass must be finite and positive")
    return grams, warnings
