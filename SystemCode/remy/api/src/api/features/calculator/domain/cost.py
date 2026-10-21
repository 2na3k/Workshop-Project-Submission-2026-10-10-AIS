import math
from decimal import Decimal, ROUND_HALF_UP

from domain.graph_vocab import PriceStatus, PriceMatchStatus, FreshnessStatus, PriceBasis
from ..models import RetailSKU
from domain.units import to_grams


def package_price(package: RetailSKU) -> float | None:
    if (package.currency != "SGD" or package.reference_price_minor is None
            or package.reference_price_minor <= 0):
        return None
    return package.reference_price_minor / 100.0


def _package_grams(package: RetailSKU) -> float | None:
    if package.price_basis == PriceBasis.PACKAGE_MASS:
        amount = package.package_mass_g
    elif package.price_basis == PriceBasis.PACKAGE_VOLUME:
        amount = package.package_volume_ml
    else:
        return None
    if amount is None or not math.isfinite(amount) or amount <= 0:
        return None
    grams, _warnings = to_grams(amount, "ml" if package.price_basis == PriceBasis.PACKAGE_VOLUME else "g")
    return grams


def select_package(packages: list[RetailSKU], grams: float) -> tuple[RetailSKU, int, float] | None:
    choices = []
    for package in packages:
        price = package_price(package)
        package_grams = _package_grams(package)
        if (package.price_status != PriceStatus.ESTIMATED
                or package.price_match_status != PriceMatchStatus.ACCEPTED
                or package.freshness_status != FreshnessStatus.FRESH or price is None
                or package_grams is None):
            continue
        count = max(1, math.ceil(grams / package_grams - 1e-9))
        choices.append((price / package_grams, count * price, -(package.confidence or 0),
                        package.food_key or "", package.retailer or "", package.listing_name or "",
                        package, count, price))
    if not choices:
        return None
    chosen = min(choices, key=lambda x: x[:6])
    return chosen[6], chosen[7], chosen[8]


def consumed_cost(package: RetailSKU, grams: float) -> float | None:
    price = package_price(package)
    package_grams = _package_grams(package)
    if price is None or package_grams is None:
        return None
    return price * grams / package_grams


def round_money(value: float | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def round_nutrient(key: str, value: float | None) -> float | None:
    if value is None:
        return None
    quantum = Decimal("1") if key == "sodium_mg" else Decimal("0.01")
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
