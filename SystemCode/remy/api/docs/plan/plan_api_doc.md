# Plan API — Frontend Documentation

**Base URL:** `/api/v1`
**Content Type:** `application/json`

---

## 📌 Overview

This API generates a **multi-day meal plan** from your recipe catalogue, subject to optional
**allergy**, **dietary**, and **nutrient** constraints. It runs a constraint solver (CP-SAT) to pick
meals per day while honouring goals, min/max limits, and variety rules.

When the plan can't be satisfied exactly, the solver walks a **relaxation ladder** (loosening
constraints step by step) and returns a `partial` plan describing exactly which constraints were
relaxed — instead of failing outright.

---

## 🔐 HTTP Status Codes

| Code  | Status                | When It Happens                                                                                                                  | What Frontend Should Do                               |
|-------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| `200` | OK                    | Plan generated (may be `complete` or `partial`)                                                                                  | Render the plan; check `status` for relaxations       |
| `400` | Bad Request           | Business logic failure (unknown allergen/dietary/nutrient code, invalid range, no candidates, infeasible plan, unsupported unit) | Show error message to user (branch on `error.code`)   |
| `422` | Unprocessable Entity  | Request body failed validation (wrong types, out-of-range values, duplicate codes, unknown fields)                               | Highlight invalid form fields using `details[].field` |
| `500` | Internal Server Error | Backend failure or timeout                                                                                                       | Show generic "something went wrong" message           |

---

## 🚨 Error Response Format (All Errors)

Every error uses the **same JSON shape**, so you can write **one generic error handler**.

### Structure

| Field                   | Type                | Description                                                   |
|-------------------------|---------------------|---------------------------------------------------------------|
| `error.code`            | `string`            | Machine-readable error code (use for branching logic)         |
| `error.message`         | `string`            | Human-readable message (safe to display directly)             |
| `error.details`         | `array[object]`     | Field-level issues (useful for form validation, may be empty) |
| `error.details[].field` | `string`            | Path to the invalid field (e.g., `nutrients.0.code`)          |
| `error.details[].issue` | `string`            | Description of what's wrong                                   |
| `error.timestamp`       | `string` (ISO 8601) | Time the error occurred                                       |

### Example

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "horizon_days",
        "issue": "Input should be less than or equal to 14"
      }
    ],
    "timestamp": "2026-09-25T03:14:16.697+00:00"
  }
}
```

---

## 1️⃣ Generate Meal Plan

```
POST /api/v1/plan
```

Generates a `horizon_days` × `meals_per_day` meal plan honouring the supplied constraints, and
returns per-day meals plus averaged horizon totals.

---

### 📤 Request Body

| Field           | Type            | Required    | Constraints            | Description                                    |
|-----------------|-----------------|-------------|------------------------|------------------------------------------------|
| `horizon_days`  | `integer`       | ✅ Required | `1` – `14`             | Number of days to plan                         |
| `meals_per_day` | `integer`       | ✅ Required | `1` – `6`              | Meals to schedule each day                     |
| `servings`      | `integer`       | ❌ Optional | min: `1`, default: `1` | Scales all ingredient quantities and nutrients |
| `allergies`     | `array[object]` | ❌ Optional | unique `code`s         | Allergens to avoid                             |
| `dietary`       | `array[object]` | ❌ Optional | unique `code`s         | Dietary restrictions to enforce                |
| `nutrients`     | `array[object]` | ❌ Optional | unique `code`s         | Nutrient goals and/or limits to target         |

> ⚠️ Unknown fields are rejected (`extra="forbid"`). Duplicate `code` values within any of
> `allergies` / `dietary` / `nutrients` cause a `422`. All string fields are whitespace-trimmed.

#### `allergies[]` Object

| Field      | Type     | Required    | Constraints              | Description                                             |
|------------|----------|-------------|--------------------------|---------------------------------------------------------|
| `code`     | `string` | ✅ Required | `1` – `64` chars         | Allergen code (normalised: lowercased, `-`/space → `_`) |
| `severity` | `string` | ❌ Optional | enum: `mild` \| `severe` | Allergy severity                                        |

> The allergen `code` is resolved server-side; an unrecognised code returns `400 UNKNOWN_ALLERGEN`.

#### `dietary[]` Object

| Field  | Type     | Required    | Constraints                   | Description              |
|--------|----------|-------------|-------------------------------|--------------------------|
| `code` | `string` | ✅ Required | enum: `halal` \| `vegetarian` | Dietary restriction code |

> Any code other than `halal` or `vegetarian` returns `400 UNKNOWN_DIETARY`.

#### `nutrients[]` Object

| Field   | Type     | Required       | Constraints                       | Description                          |
|---------|----------|----------------|-----------------------------------|--------------------------------------|
| `code`  | `string` | ✅ Required    | see **Supported Nutrients** below | Nutrient code                        |
| `unit`  | `string` | ✅ Required    | `1` – `16` chars                  | Unit label for the goal/limit values |
| `goal`  | `object` | ⚠️ Conditional | —                                 | Target value (soft objective)        |
| `limit` | `object` | ⚠️ Conditional | —                                 | Hard min/max bounds                  |

> ⚠️ **At least one of `goal` or `limit` is required** per nutrient — otherwise `422`.

##### `nutrients[].goal` Object

| Field   | Type     | Required    | Constraints    | Description                      |
|---------|----------|-------------|----------------|----------------------------------|
| `value` | `number` | ✅ Required | must be finite | Per-day target for this nutrient |

##### `nutrients[].limit` Object

| Field | Type     | Required    | Constraints           | Description         |
|-------|----------|-------------|-----------------------|---------------------|
| `min` | `number` | ❌ Optional | finite; `min` ≤ `max` | Per-day lower bound |
| `max` | `number` | ❌ Optional | finite; `min` ≤ `max` | Per-day upper bound |

> `min` > `max` returns `422` at validation, or `400 INVALID_NUTRIENT_RANGE` at the service layer.

#### Supported Nutrients

| `code`          | Unit |
|-----------------|------|
| `calories`      | kcal |
| `protein`       | g    |
| `carbs`         | g    |
| `fat`           | g    |
| `saturated_fat` | g    |
| `fiber`         | g    |
| `sugar`         | g    |
| `sodium`        | mg   |
| `cholesterol`   | mg   |

> Any other nutrient `code` returns `400 UNKNOWN_NUTRIENT`.

### Request Example

```json
{
  "horizon_days": 3,
  "meals_per_day": 3,
  "servings": 2,
  "allergies": [
    {
      "code": "peanut",
      "severity": "severe"
    }
  ],
  "dietary": [
    {
      "code": "vegetarian"
    }
  ],
  "nutrients": [
    {
      "code": "calories",
      "unit": "kcal",
      "goal": {
        "value": 2000
      }
    },
    {
      "code": "protein",
      "unit": "g",
      "limit": {
        "min": 60,
        "max": 120
      }
    }
  ]
}
```

---

### 📥 Success Response — `200 OK`

#### Top-Level Fields

| Field                | Type            | Nullable | Description                                                             |
|----------------------|-----------------|----------|-------------------------------------------------------------------------|
| `plan_id`            | `string`        | No       | Unique plan identifier (e.g., `"plan_a1b2c3d4e5"`)                      |
| `status`             | `string`        | No       | `"complete"` (no relaxations) or `"partial"` (some constraints relaxed) |
| `message`            | `string`        | No       | Human-readable summary (safe to display)                                |
| `validation_summary` | `object`        | No       | Allergen/dietary check outcome (see below)                              |
| `relaxations`        | `array[object]` | No       | Constraints that were loosened to reach a plan (empty when `complete`)  |
| `horizon_totals`     | `object`        | No       | Average daily nutrient totals across the whole horizon (see below)      |
| `days`               | `array[object]` | No       | One entry per planned day, in order                                     |

#### `validation_summary` Object

| Field             | Type     | Description                                                        |
|-------------------|----------|--------------------------------------------------------------------|
| `allergen_status` | `string` | `"passed"` if allergies were requested, else `"not_requested"`     |
| `dietary_status`  | `string` | `"passed"` if dietary codes were requested, else `"not_requested"` |

#### `relaxations[]` Object

Present only when the solver had to loosen constraints. Each record is applied cumulatively.

| Field    | Type      | Description                                          |
|----------|-----------|------------------------------------------------------|
| `stage`  | `integer` | Ladder stage the relaxation was applied at (`1`–`4`) |
| `kind`   | `string`  | Which constraint was relaxed (see table below)       |
| `detail` | `object`  | Stage-specific specifics (may be empty)              |

##### Relaxation Kinds

| `stage` | `kind`                  | Meaning                                               | `detail` shape                                              |
|---------|-------------------------|-------------------------------------------------------|-------------------------------------------------------------|
| `1`     | `extra_days_per_recipe` | Allowed each recipe to repeat on one more day         | `{ "added": 1 }`                                            |
| `2`     | `drop_consecutive_rule` | Dropped the "no same recipe on consecutive days" rule | `{}`                                                        |
| `3`     | `widen_nutrient_max`    | Raised every nutrient `max` by 10%                    | `{ "nutrients": [{ "code", "from", "to" }] }` (milli-units) |
| `4`     | `loosen_nutrient_min`   | Lowered every nutrient `min` by 10%                   | `{ "nutrients": [{ "code", "from", "to" }] }` (milli-units) |

> ℹ️ `from`/`to` values in `widen_nutrient_max` / `loosen_nutrient_min` are internal **milli-units**
> (value × 1000). Use them for display of "what changed", not for arithmetic against request values.

#### `horizon_totals` Object

Averaged daily totals keyed by `avg_daily_<nutrient_key>`, e.g. `avg_daily_calories`,
`avg_daily_protein_g`, `avg_daily_sodium_mg`. Keys depend on which nutrients the matched recipes
carry; values are `number` and already scaled by `servings`.

```json
{
  "avg_daily_calories": 1985.4,
  "avg_daily_protein_g": 98.2,
  "avg_daily_carbs_g": 210.6,
  "avg_daily_fat_g": 61.3
}
```

#### `days[]` Object

| Field   | Type            | Nullable | Description                  |
|---------|-----------------|----------|------------------------------|
| `day`   | `integer`       | No       | 1-based day index            |
| `meals` | `array[object]` | No       | Meals for that day (ordered) |

> Within a day, meals are ordered by **descending calories**, then **ascending `recipe_id`**.

#### `days[].meals[]` Object

| Field          | Type            | Nullable | Description                                                  |
|----------------|-----------------|----------|--------------------------------------------------------------|
| `slot`         | `string`        | No       | Meal slot label (`meal_1`, `meal_2`, …)                      |
| `recipe_id`    | `string`        | No       | Recipe identifier                                            |
| `title`        | `string`        | No       | Recipe title                                                 |
| `nutrients`    | `object`        | No       | Nutrient map for this meal, scaled by `servings` (see below) |
| `ingredients`  | `array[object]` | No       | Ingredient list (ordered by original position)               |
| `instructions` | `string`        | ✅ Yes   | Preparation instructions, `null` if unavailable              |

> `nutrients` is a flat `{ key: number }` map (e.g. `calories`, `protein_g`, `sodium_mg`). Only
> non-null nutrients are included, each rounded to 2 decimals and multiplied by `servings`.

#### `days[].meals[].ingredients[]` Object

| Field         | Type      | Nullable | Description                                                        |
|---------------|-----------|----------|--------------------------------------------------------------------|
| `quantity`    | `number`  | ✅ Yes   | Amount, scaled by `servings`; `null` if not specified              |
| `unit`        | `string`  | ✅ Yes   | Unit of measure; `null` if not specified                           |
| `text`        | `string`  | ✅ Yes   | Best-available ingredient text (cleaned/raw/description/canonical) |
| `preparation` | `string`  | ✅ Yes   | Prep note (e.g. `"diced"`); `null` if none                         |
| `optional`    | `boolean` | No       | Whether the ingredient is optional                                 |

---

### Success Response Example

```json
{
  "plan_id": "plan_a1b2c3d4e5",
  "status": "partial",
  "message": "Successfully generated a 3-day meal plan.",
  "validation_summary": {
    "allergen_status": "passed",
    "dietary_status": "passed"
  },
  "relaxations": [
    {
      "stage": 3,
      "kind": "widen_nutrient_max",
      "detail": {
        "nutrients": [
          {
            "code": "protein",
            "from": 120000,
            "to": 132000
          }
        ]
      }
    }
  ],
  "horizon_totals": {
    "avg_daily_calories": 1985.4,
    "avg_daily_protein_g": 98.2,
    "avg_daily_carbs_g": 210.6,
    "avg_daily_fat_g": 61.3
  },
  "days": [
    {
      "day": 1,
      "meals": [
        {
          "slot": "meal_1",
          "recipe_id": "r_1042",
          "title": "Chickpea & Spinach Curry",
          "nutrients": {
            "calories": 640.0,
            "protein_g": 28.5,
            "carbs_g": 82.0,
            "fat_g": 18.4
          },
          "ingredients": [
            {
              "quantity": 200.0,
              "unit": "g",
              "text": "canned chickpeas",
              "preparation": "drained",
              "optional": false
            },
            {
              "quantity": 100.0,
              "unit": "g",
              "text": "baby spinach",
              "preparation": null,
              "optional": false
            }
          ],
          "instructions": "Sauté aromatics, add chickpeas and spinach, simmer 15 min."
        }
      ]
    }
  ]
}
```

---

## ❌ Error Responses

All business-logic failures below return **`400 Bad Request`** with the standard error envelope.

### `400` — Business Logic Errors

| `error.code`             | When It Happens                                                 |
|--------------------------|-----------------------------------------------------------------|
| `UNKNOWN_ALLERGEN`       | An `allergies[].code` could not be resolved                     |
| `UNKNOWN_DIETARY`        | A `dietary[].code` is not `halal` or `vegetarian`               |
| `UNKNOWN_NUTRIENT`       | A `nutrients[].code` is not in the supported list               |
| `INVALID_NUTRIENT_RANGE` | A nutrient's `limit.min` exceeds its `limit.max`                |
| `NO_CANDIDATES`          | No recipes with usable nutrition data survived filtering        |
| `UNSUPPORTED_UNIT`       | No recipe could be converted to grams for nutrition calculation |
| `PLAN_INFEASIBLE`        | No feasible plan exists even after all relaxations              |

```json
{
  "error": {
    "code": "UNKNOWN_NUTRIENT",
    "message": "Unknown nutrient: vitamin_c",
    "details": [],
    "timestamp": "2026-09-25T03:14:16.697+00:00"
  }
}
```

**Frontend tip:** `details` is empty for these — parse the offending value out of `message` if you
need to highlight the field.

### `422 Unprocessable Entity` — Validation Error

Occurs when the request body violates schema rules (wrong type, out-of-range, duplicate code,
unknown field, missing `goal`/`limit`, etc.).

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "meals_per_day",
        "issue": "Input should be less than or equal to 6"
      }
    ],
    "timestamp": "2026-09-25T03:14:16.697+00:00"
  }
}
```

**Frontend tip:** `details[].field` uses **dot notation with array indices** (`nutrients.0.code` =
first nutrient's code). Map these directly to your form input refs.

---

## 🧑‍💻 Frontend Integration Cheat Sheet

```js
async function generatePlan(payload) {
    const res = await fetch('/api/v1/plan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
        // Uniform error envelope for ALL error statuses
        throw new ApiError(res.status, data.error.code, data.error.message, data.error.details);
    }

    return data; // { plan_id, status, message, validation_summary, relaxations, horizon_totals, days }
}
```

**Key reminders:**

1. ⚠️ **Check `status`** — a `200` can still be `"partial"`. Surface `relaxations` so the user knows
   which constraints were loosened.
2. ✅ **Null-check** `instructions`, and each ingredient's `quantity`/`unit`/`preparation` before
   display.
3. 📏 **Validate ranges client-side**: `horizon_days` `1`–`14`, `meals_per_day` `1`–`6`,
   `servings` ≥ `1` to avoid `422` round-trips.
4. 🔢 **Every nutrient needs `goal` or `limit`** — enforce before submitting.
5. 🔁 **De-duplicate codes** within `allergies` / `dietary` / `nutrients` client-side.
6. 🧮 **`servings` scales output** — meal `nutrients`, ingredient `quantity`, and `horizon_totals`
   are all already multiplied by `servings`; don't scale again.
7. 📊 **`horizon_totals` keys are dynamic** (`avg_daily_*`) — iterate the object rather than
   assuming a fixed set.
