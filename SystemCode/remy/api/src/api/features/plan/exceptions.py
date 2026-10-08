from api.core.exceptions import AppError
from .models import NamedConstraint


class PlanError(AppError): pass


class UnknownAllergen(PlanError): status_code, code = 400, "UNKNOWN_ALLERGEN"


class UnknownDietary(PlanError): status_code, code = 400, "UNKNOWN_DIETARY"
class UnknownNutrient(PlanError): status_code, code = 400, "UNKNOWN_NUTRIENT"


class NoCandidates(PlanError): status_code, code = 400, "NO_CANDIDATES"


class InvalidNutrientRange(PlanError): status_code, code = 400, "INVALID_NUTRIENT_RANGE"


class PlanInfeasible(PlanError):
    status_code, code = 400, "PLAN_INFEASIBLE"

    def __init__(
        self,
        message: str,
        binding_constraints: list[NamedConstraint] | None = None,
        reason: str = "no-assignment",
    ):
        self.binding_constraints = list(binding_constraints or [])
        self.reason = reason
        details = [{"field": "reason", "issue": reason}] + [
            {
                "field": constraint.scope,
                "issue": f"{constraint.code}:{constraint.kind}",
            }
            for constraint in self.binding_constraints
        ]
        super().__init__(message, details=details)


class SolverUnavailable(PlanError): status_code, code = 503, "SOLVER_UNAVAILABLE"


class UnsupportedUnit(PlanError): status_code, code = 400, "UNSUPPORTED_UNIT"
