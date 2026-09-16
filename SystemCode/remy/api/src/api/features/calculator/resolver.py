import re
import unicodedata
from difflib import SequenceMatcher
from .exceptions import AmbiguousIngredient, UnresolvableIngredient
from .synonyms import ALIASES


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def _token_score(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    token = len(sa & sb) / max(len(sa | sb), 1)
    return max(SequenceMatcher(None, a, b).ratio(), token)


def resolve(name: str, canonical_keys: list[str], fuzzy_candidates: list[str] | None = None) -> tuple[str, str, float | None]:
    normalized = normalize_name(name)
    normalized_keys = {normalize_name(k): k for k in canonical_keys}
    if normalized in normalized_keys:
        return normalized_keys[normalized], "exact", 1.0
    alias = ALIASES.get(normalized)
    if alias and alias in normalized_keys:
        return normalized_keys[alias], "alias", 1.0
    candidates = fuzzy_candidates if fuzzy_candidates is not None else canonical_keys
    scored = sorted(((key, _token_score(normalized, normalize_name(key))) for key in candidates),
                    key=lambda x: (-x[1], x[0]))[:20]
    if not scored:
        raise UnresolvableIngredient(f"Ingredient '{name}' could not be resolved")
    if scored[0][1] < 0.86 or (len(scored) > 1 and scored[0][1] - scored[1][1] < 0.05):
        raise AmbiguousIngredient(f"Ingredient '{name}' is ambiguous", [{"field": "name", "issue": str(scored[:3])}])
    return scored[0][0], "fuzzy", scored[0][1]
