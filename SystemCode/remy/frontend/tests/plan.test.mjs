import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";
import {
  describeRelaxation,
  formatIngredient,
  formatNutrient,
  generatePlan,
  nutrientInfo,
  sortedNutrients,
} from "../src/lib/plan-api.ts";

afterEach(() => mock.restoreAll());

const request = {
  horizon_days: 3,
  meals_per_day: 3,
  servings: 2,
  allergies: [{ code: "peanut" }],
  dietary: [{ code: "vegetarian" }],
  nutrients: [
    { code: "calories", unit: "kcal", goal: { value: 2000 } },
    { code: "protein", unit: "g", limit: { min: 60, max: 120 } },
  ],
};

const plan = {
  plan_id: "plan_a1b2c3d4e5",
  status: "complete",
  message: "Successfully generated a 3-day meal plan.",
  validation_summary: { allergen_status: "passed", dietary_status: "passed" },
  relaxations: [],
  horizon_totals: { avg_daily_calories: 1985.4 },
  days: [],
};

test("plan requests go through the /api/v1 proxy as JSON", async () => {
  const fetchMock = mock.method(globalThis, "fetch", async () => Response.json(plan));
  assert.deepEqual(await generatePlan(request), plan);
  const [url, options] = fetchMock.mock.calls[0].arguments;
  assert.equal(url, "/api/v1/plan");
  assert.equal(options.method, "POST");
  assert.equal(options.credentials, "omit");
  assert.deepEqual(JSON.parse(options.body), request);
});

test("empty limit bounds are dropped from the payload", async () => {
  const fetchMock = mock.method(globalThis, "fetch", async () => Response.json(plan));
  await generatePlan({
    horizon_days: 7,
    meals_per_day: 3,
    servings: 1,
    nutrients: [{ code: "sodium", unit: "mg", limit: { min: undefined, max: 2300 } }],
  });
  assert.deepEqual(JSON.parse(fetchMock.mock.calls[0].arguments[1].body).nutrients, [
    { code: "sodium", unit: "mg", limit: { max: 2300 } },
  ]);
});

test("out-of-range plans and incomplete nutrient targets are rejected before a request", async () => {
  const fetchMock = mock.method(globalThis, "fetch", async () => { throw new Error("must not call"); });
  for (const horizon_days of [0, 15, 2.5, NaN]) {
    await assert.rejects(generatePlan({ ...request, horizon_days }), /1 and 14 days/);
  }
  for (const meals_per_day of [0, 7, 1.5]) {
    await assert.rejects(generatePlan({ ...request, meals_per_day }), /1 and 6 meals/);
  }
  for (const servings of [0, -1, 1.5]) {
    await assert.rejects(generatePlan({ ...request, servings }), /servings/);
  }
  await assert.rejects(
    generatePlan({ ...request, nutrients: [{ code: "fiber", unit: "g" }] }),
    /Give Fibre a target/,
  );
  await assert.rejects(
    generatePlan({ ...request, nutrients: [{ code: "fat", unit: "g", limit: { min: 90, max: 40 } }] }),
    /Fat minimum cannot be greater/,
  );
  await assert.rejects(
    generatePlan({ ...request, nutrients: [request.nutrients[0], request.nutrients[0]] }),
    /Calories is listed more than once/,
  );
  await assert.rejects(
    generatePlan({ ...request, nutrients: [{ code: "sugar", unit: "g", goal: { value: Infinity } }] }),
    /numbers of 0 or more/,
  );
  assert.equal(fetchMock.mock.callCount(), 0);
});

test("API errors use friendly copy for planner failures and the envelope otherwise", async () => {
  const fetchMock = mock.method(globalThis, "fetch", async () => Response.json({ error: {
    code: "PLAN_INFEASIBLE", message: "No feasible plan after all relaxations", details: [],
  } }, { status: 400 }));
  await assert.rejects(generatePlan(request), /No plan fits these settings/);

  fetchMock.mock.mockImplementation(async () => Response.json({ error: {
    code: "VALIDATION_ERROR",
    message: "Request validation failed",
    details: [{ field: "meals_per_day", issue: "Input should be less than or equal to 6" }],
  } }, { status: 422 }));
  await assert.rejects(generatePlan(request), /Request validation failed Input should be less than or equal to 6/);

  fetchMock.mock.mockImplementation(async () => Response.json({ error: {
    code: "UNKNOWN_ALLERGEN", message: "Unknown allergen: tree_nut", details: [],
  } }, { status: 400 }));
  await assert.rejects(generatePlan(request), /Unknown allergen: tree_nut/);
});

test("offline, timeout, and malformed responses give useful messages", async () => {
  const fetchMock = mock.method(globalThis, "fetch", async () => { throw new TypeError("fetch failed"); });
  await assert.rejects(generatePlan(request), /Cannot reach the meal planner/);
  fetchMock.mock.mockImplementation(async () => { throw new DOMException("Timeout", "TimeoutError"); });
  await assert.rejects(generatePlan(request), /took too long/);
  fetchMock.mock.mockImplementation(async () => new Response("Bad gateway", { status: 502 }));
  await assert.rejects(generatePlan(request), /planner is unavailable/);
  fetchMock.mock.mockImplementation(async () => Response.json({ status: "success" }));
  await assert.rejects(generatePlan(request), /unexpected response/);
});

test("nutrient keys from totals and meals map to labels and units", () => {
  assert.deepEqual(
    [nutrientInfo("avg_daily_protein_g"), nutrientInfo("calories"), nutrientInfo("avg_daily_vitamin_c_mg")]
      .map(({ label, unit }) => [label, unit]),
    [["Protein", "g"], ["Calories", "kcal"], ["Vitamin c", "mg"]],
  );
  assert.equal(formatNutrient("avg_daily_sodium_mg", 1234.56), "1,234.6 mg");
  assert.deepEqual(
    sortedNutrients({ fat_g: 1, unknown_g: 2, calories: 3, protein_g: 4 }).map(([key]) => key),
    ["calories", "protein_g", "fat_g", "unknown_g"],
  );
});

test("ingredients and relaxations read as plain sentences", () => {
  assert.equal(
    formatIngredient({ quantity: 200, unit: "g", text: "canned chickpeas", preparation: "drained", optional: false }),
    "200 g canned chickpeas, drained",
  );
  assert.equal(
    formatIngredient({ quantity: 0.3333, unit: null, text: "lemon", preparation: null, optional: true }),
    "0.33 lemon",
  );
  assert.equal(
    formatIngredient({ quantity: null, unit: null, text: null, preparation: null, optional: false }),
    "Unnamed ingredient",
  );
  assert.equal(
    describeRelaxation({ stage: 1, kind: "extra_days_per_recipe", detail: { added: 1 } }),
    "Let each recipe repeat on 1 more day.",
  );
  assert.equal(
    describeRelaxation({ stage: 3, kind: "widen_nutrient_max", detail: { nutrients: [{ code: "protein", from: 120000, to: 132000 }] } }),
    "Raised the daily maximum for protein from 120 to 132 g.",
  );
});
