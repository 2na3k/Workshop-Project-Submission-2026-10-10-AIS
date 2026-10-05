import {
  describeRelaxation,
  formatIngredient,
  formatNutrient,
  nutrientInfo,
  sortedNutrients,
  type PlanMeal,
  type PlanResponse,
} from "@/lib/plan-api";

const HEADLINE = new Set(["calories", "protein_g", "carbs_g", "fat_g"]);

export default function PlanView({ plan, servings, overview }: { plan: PlanResponse; servings: number; overview?: string }) {
  const totals = sortedNutrients(plan.horizon_totals);
  const complete = plan.status === "complete";

  return (
    <section aria-labelledby="plan-heading" className="mt-12 border-t border-subtle pt-10">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="plan-heading" className="text-3xl font-extrabold tracking-tight">
          Your {plan.days.length}-day plan
        </h2>
        <span
          className={`rounded-full px-3 py-1 text-xs font-bold ${
            complete ? "bg-sage text-sage-foreground" : "bg-accent/10 text-accent"
          }`}
        >
          {complete ? "Complete" : "Adjusted to fit"}
        </span>
      </div>
      <p className="mt-2 text-sm text-muted">
        {plan.message}
        {servings > 1 && ` Amounts are for ${servings} servings.`}
      </p>
      {overview?.trim() && (
        <p className="mt-4 whitespace-pre-line text-sm leading-relaxed">{overview.trim()}</p>
      )}

      {plan.relaxations.length > 0 && (
        <div className="mt-5 rounded-2xl bg-cream p-4 text-sm">
          <p className="font-bold">To make everything fit, the planner:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
            {plan.relaxations.map((relaxation) => (
              <li key={`${relaxation.stage}-${relaxation.kind}`}>{describeRelaxation(relaxation)}</li>
            ))}
          </ul>
        </div>
      )}

      {totals.length > 0 && (
        <>
          <h3 className="mt-8 text-sm font-bold">Average per day</h3>
          <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {totals.map(([key, value]) => (
              <div key={key} className="rounded-2xl bg-sage/50 p-4">
                <dt className="text-xs font-semibold text-muted">{nutrientInfo(key).label}</dt>
                <dd className="mt-1 text-lg font-bold tabular-nums">{formatNutrient(key, value)}</dd>
              </div>
            ))}
          </dl>
        </>
      )}

      <ol className="mt-10 space-y-10">
        {plan.days.map((day) => (
          <li key={day.day}>
            <h3 className="eyebrow">Day {day.day}</h3>
            <ul className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {day.meals.map((meal) => (
                <MealCard key={meal.slot} meal={meal} />
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function MealCard({ meal, label }: { meal: PlanMeal; label?: string }) {
  const headline = sortedNutrients(meal.nutrients).filter(([key]) => HEADLINE.has(key));

  return (
    <li className="flex flex-col rounded-2xl border border-subtle bg-surface p-4">
      <p className="text-xs font-semibold text-muted">{label ?? meal.slot.replace(/^meal_/, "Meal ")}</p>
      <h4 className="mt-1 font-bold leading-snug">{meal.title}</h4>
      {headline.length > 0 && (
        <p className="mt-1.5 text-sm text-muted tabular-nums">
          {headline
            .map(([key, value]) =>
              key === "calories"
                ? formatNutrient(key, value)
                : `${formatNutrient(key, value)} ${nutrientInfo(key).label.toLowerCase()}`,
            )
            .join(" · ")}
        </p>
      )}

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-semibold text-accent">Ingredients &amp; method</summary>
        {meal.ingredients.length > 0 && (
          <ul className="mt-3 space-y-1">
            {meal.ingredients.map((ingredient, index) => (
              <li key={index} className="leading-snug">
                {formatIngredient(ingredient)}
                {ingredient.optional && <span className="text-muted"> (optional)</span>}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 whitespace-pre-line leading-relaxed text-muted">
          {meal.instructions?.trim() || "No method available for this recipe."}
        </p>
      </details>
    </li>
  );
}
