export const PLAN_NUTRIENTS = [
  { code: "calories", key: "calories", label: "Calories", unit: "kcal" },
  { code: "protein", key: "protein_g", label: "Protein", unit: "g" },
  { code: "carbs", key: "carbs_g", label: "Carbohydrates", unit: "g" },
  { code: "fat", key: "fat_g", label: "Fat", unit: "g" },
  { code: "saturated_fat", key: "saturated_fat_g", label: "Saturated fat", unit: "g" },
  { code: "fiber", key: "fiber_g", label: "Fibre", unit: "g" },
  { code: "sugar", key: "sugar_g", label: "Sugar", unit: "g" },
  { code: "sodium", key: "sodium_mg", label: "Sodium", unit: "mg" },
  { code: "cholesterol", key: "cholesterol_mg", label: "Cholesterol", unit: "mg" },
] as const;

export const ALLERGENS = [
  { code: "peanut", label: "Peanuts" },
  { code: "milk", label: "Milk & dairy" },
  { code: "egg", label: "Eggs" },
  { code: "wheat", label: "Wheat & gluten" },
  { code: "soy", label: "Soy" },
  { code: "fish", label: "Fish" },
  { code: "shellfish", label: "Shellfish" },
  { code: "sesame", label: "Sesame" },
  { code: "mustard", label: "Mustard" },
  { code: "celery", label: "Celery" },
  { code: "lupin", label: "Lupin" },
  { code: "sulphites", label: "Sulphites" },
] as const;

export const DIETARY = [
  { code: "halal", label: "Halal" },
  { code: "vegetarian", label: "Vegetarian" },
] as const;

export type NutrientCode = (typeof PLAN_NUTRIENTS)[number]["code"];
export type AllergenCode = (typeof ALLERGENS)[number]["code"];
export type DietaryCode = (typeof DIETARY)[number]["code"];

export type NutrientTarget = {
  code: NutrientCode;
  unit: string;
  goal?: { value: number };
  limit?: { min?: number; max?: number };
};

export type PlanRequest = {
  horizon_days: number;
  meals_per_day: number;
  servings: number;
  allergies?: { code: AllergenCode; severity?: "mild" | "severe" }[];
  dietary?: { code: DietaryCode }[];
  nutrients?: NutrientTarget[];
};

export type PlanIngredient = {
  quantity: number | null;
  unit: string | null;
  text: string | null;
  preparation: string | null;
  optional: boolean;
};

export type PlanMeal = {
  slot: string;
  recipe_id: string;
  title: string;
  nutrients: Record<string, number>;
  ingredients: PlanIngredient[];
  instructions: string | null;
};

export type PlanDay = { day: number; meals: PlanMeal[] };

export type Relaxation = {
  stage: number;
  kind: string;
  detail: {
    added?: number;
    nutrients?: { code: string; from: number; to: number }[];
  };
};

export type PlanResponse = {
  plan_id: string;
  status: "complete" | "partial";
  message: string;
  validation_summary: Record<string, string>;
  relaxations: Relaxation[];
  horizon_totals: Record<string, number>;
  days: PlanDay[];
};

const FRIENDLY_ERRORS: Record<string, string> = {
  NO_CANDIDATES: "No recipes with complete nutrition data are available for these settings.",
  UNSUPPORTED_UNIT: "None of the recipes could be measured in grams, so a plan can't be built yet.",
  PLAN_INFEASIBLE: "No plan fits these settings, even after loosening them. Try fewer meals a day or wider nutrient ranges.",
  INTERNAL_ERROR: "The planner ran into a problem. Please try again.",
};

const isWhole = (value: number, min: number, max = Number.POSITIVE_INFINITY) =>
  Number.isInteger(value) && value >= min && value <= max;

function validate(request: PlanRequest) {
  if (!isWhole(request.horizon_days, 1, 14)) {
    throw new Error("Plan between 1 and 14 days.");
  }
  if (!isWhole(request.meals_per_day, 1, 6)) {
    throw new Error("Choose between 1 and 6 meals a day.");
  }
  if (!isWhole(request.servings, 1)) {
    throw new Error("Enter a whole number of servings, 1 or more.");
  }

  const seen = new Set<string>();
  for (const nutrient of request.nutrients ?? []) {
    const label = PLAN_NUTRIENTS.find((item) => item.code === nutrient.code)?.label ?? nutrient.code;
    if (seen.has(nutrient.code)) {
      throw new Error(`${label} is listed more than once.`);
    }
    seen.add(nutrient.code);

    const values = [nutrient.goal?.value, nutrient.limit?.min, nutrient.limit?.max]
      .filter((value) => value !== undefined);
    if (!values.length) {
      throw new Error(`Give ${label} a target, a minimum, or a maximum.`);
    }
    if (values.some((value) => !Number.isFinite(value) || value < 0)) {
      throw new Error(`${label} amounts must be numbers of 0 or more.`);
    }
    const { min, max } = nutrient.limit ?? {};
    if (min !== undefined && max !== undefined && min > max) {
      throw new Error(`${label} minimum cannot be greater than its maximum.`);
    }
  }
}

export async function generatePlan(request: PlanRequest): Promise<PlanResponse> {
  validate(request);

  let response: Response;
  try {
    response = await fetch("/api/v1/plan", {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(60_000),
    });
  } catch (error) {
    if (error instanceof Error && error.name === "TimeoutError") {
      throw new Error("Building the plan took too long. Please try again.");
    }
    throw new Error("Cannot reach the meal planner. Please try again.");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const code = payload?.error?.code;
    const message = payload?.error?.message;
    const details: unknown = payload?.error?.details;
    const issues = Array.isArray(details)
      ? details.flatMap((detail) => typeof detail?.issue === "string" ? [detail.issue] : [])
      : [];
    throw new Error([
      (typeof code === "string" && FRIENDLY_ERRORS[code]) ||
        (typeof message === "string" ? message : "The meal planner is unavailable. Please try again."),
      ...issues,
    ].join(" "));
  }
  if (!payload || typeof payload.plan_id !== "string" || !Array.isArray(payload.days) ||
      !Array.isArray(payload.relaxations) || typeof payload.horizon_totals !== "object") {
    throw new Error("The meal planner returned an unexpected response. Please try again.");
  }
  return payload as PlanResponse;
}

const AMOUNT = new Intl.NumberFormat("en-SG", { maximumFractionDigits: 1 });
const QUANTITY = new Intl.NumberFormat("en-SG", { maximumFractionDigits: 2 });

export function nutrientInfo(key: string) {
  const bare = key.replace(/^avg_daily_/, "");
  const known = PLAN_NUTRIENTS.find((item) => item.key === bare || item.code === bare);
  if (known) return { label: known.label, unit: known.unit, order: PLAN_NUTRIENTS.indexOf(known) };
  const unit = bare.endsWith("_mg") ? "mg" : bare.endsWith("_g") ? "g" : bare.endsWith("_kcal") ? "kcal" : "";
  const name = bare.replace(/_(mg|g|kcal)$/, "").replaceAll("_", " ");
  return { label: name.charAt(0).toUpperCase() + name.slice(1), unit, order: PLAN_NUTRIENTS.length };
}

export function formatNutrient(key: string, value: number) {
  const { unit } = nutrientInfo(key);
  return unit ? `${AMOUNT.format(value)} ${unit}` : AMOUNT.format(value);
}

export function sortedNutrients(values: Record<string, number>) {
  return Object.entries(values).sort(
    ([a], [b]) => nutrientInfo(a).order - nutrientInfo(b).order || a.localeCompare(b),
  );
}

export function formatIngredient(ingredient: PlanIngredient) {
  const amount = [
    ingredient.quantity == null ? null : QUANTITY.format(ingredient.quantity),
    ingredient.unit,
  ].filter(Boolean).join(" ");
  const name = ingredient.text ?? "Unnamed ingredient";
  const preparation = ingredient.preparation ? `, ${ingredient.preparation}` : "";
  return `${amount ? `${amount} ` : ""}${name}${preparation}`;
}

export function describeRelaxation(relaxation: Relaxation) {
  const changes = (relaxation.detail.nutrients ?? []).map(({ code, from, to }) => {
    const nutrient = PLAN_NUTRIENTS.find((item) => item.code === code);
    const unit = nutrient ? ` ${nutrient.unit}` : "";
    return `${nutrient?.label.toLowerCase() ?? code} from ${AMOUNT.format(from / 1000)} to ${AMOUNT.format(to / 1000)}${unit}`;
  }).join(", ");

  switch (relaxation.kind) {
    case "extra_days_per_recipe": {
      const added = relaxation.detail.added ?? 1;
      return `Let each recipe repeat on ${added} more ${added === 1 ? "day" : "days"}.`;
    }
    case "drop_consecutive_rule":
      return "Allowed the same recipe on back-to-back days.";
    case "widen_nutrient_max":
      return `Raised the daily maximum for ${changes}.`;
    case "loosen_nutrient_min":
      return `Lowered the daily minimum for ${changes}.`;
    default:
      return `${relaxation.kind.replaceAll("_", " ")}.`;
  }
}
