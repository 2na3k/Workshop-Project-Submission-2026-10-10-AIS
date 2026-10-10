from enum import StrEnum


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    UNKNOWN = "unknown"


class PriceStatus(StrEnum):
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class PriceMatchStatus(StrEnum):
    ACCEPTED = "accepted"
    ESTIMATED = "estimated"
    UNMATCHED = "unmatched"


class PriceBasis(StrEnum):
    PACKAGE_MASS = "package_mass"
    PACKAGE_VOLUME = "package_volume"
    PACKAGE_UNRESOLVED = "package_unresolved"
    SPAN_REFERENCE = "span_reference"
    NUTRITION_ONLY = "nutrition_only"


class Currency(StrEnum):
    SGD = "SGD"


class ApprovalStatus(StrEnum):
    ACCEPTED = "accepted"


class NutritionSource(StrEnum):
    CRAWLER_FDC_PROFILE = "crawler_fdc_profile"
    FOODDATA_CENTRAL = "fooddata_central"

class AllergenScreeningStatus(StrEnum):
    UNKNOWN = "unknown"

COST_CONVERTIBLE_BASES = frozenset({PriceBasis.PACKAGE_MASS, PriceBasis.PACKAGE_VOLUME})
FRESH_VALUES = frozenset({FreshnessStatus.FRESH})
