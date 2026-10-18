# Remy API Specification (v1)

This document outlines the REST and Streaming API endpoints for the Remy Meal Planning Service.
Built with **FastAPI** (Python) on the backend and tailored for **JavaScript/TypeScript** client
integration, all endpoints use JSON request/response payloads unless specified otherwise (e.g.,
Server-Sent Events).

---

## Standard Conventions & Errors

* **Base URL**: `[https://api.remy.app/api/v1](https://api.remy.app/api/v1)` (Prod) /
  `http://localhost:8000/api/v1` (Local)
* **Headers**:
* `Content-Type: application/json`
* `Accept: application/json` (or `text/event-stream` for SSE)


* **Standard Error Response** (FastAPI Pydantic default):

```json
{
  "detail": [
    {
      "loc": [
        "body",
        "nutrients",
        0,
        "code"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

```

---

## Technical Standards & Error Handling

### HTTP Status Codes

| Code  | Status                | Trigger Condition                                                                   |
|-------|-----------------------|-------------------------------------------------------------------------------------|
| `200` | OK                    | Successful request execution.                                                       |
| `400` | Bad Request           | Business logic error (e.g., unresolvable recipe concept, invalid unit conversions). |
| `404` | Not Found             | Requested entity (`recipe_id`, `session_id`) does not exist.                        |
| `422` | Unprocessable Entity  | Schema or type validation failure (FastAPI Pydantic error).                         |
| `500` | Internal Server Error | Unhandled backend failure, database execution fault, or downstream service timeout. |

### Standard Error Response Envelope

All error responses return a standardized JSON envelope to simplify client-side exception handling
in JavaScript.

```json
{
  "error": {
    "code": "INVALID_NUTRIENT_RANGE",
    "message": "Nutrient limit 'min' cannot be greater than 'max'.",
    "details": [
      {
        "field": "nutrients[0].limit",
        "issue": "min (2200) > max (1800)"
      }
    ],
    "timestamp": "2026-09-16T01:00:00Z"
  }
}

```

---

## 1. POST `/api/v1/calculate/cost-and-nutrition`

Evaluates exact macronutrient/micronutrient profiles and distinguishes **consumed ingredient costs**
from **whole-package retail pricing** based on grocery data.

### Request Parameters

| Field                    | Type            | In   | Nullable / Required | Description                                      |
|--------------------------|-----------------|------|---------------------|--------------------------------------------------|
| `servings`               | `integer`       | Body | Required            | Number of target servings (min: 1).              |
| `ingredients`            | `array[object]` | Body | Required            | List of raw or canonical ingredients to analyze. |
| `ingredients[].name`     | `string`        | Body | Required            | Ingredient title or food name.                   |
| `ingredients[].quantity` | `number`        | Body | Required            | Numerical quantity (must be > 0).                |
| `ingredients[].unit`     | `string`        | Body | Required            | Unit of measure (`g`, `kg`, `ml`, `tbsp`,`pc`).  |

### Request Body Example

```json
{
  "servings": 2,
  "ingredients": [
    {
      "name": "Chicken Breast",
      "quantity": 300,
      "unit": "g"
    },
    {
      "name": "Rolled Oats",
      "quantity": 100,
      "unit": "g"
    }
  ]
}

```

### Response (`200 OK`)

```json
{
  "status": "success",
  "servings": 2,
  "summary": {
    "total_consumed_cost_sgd": null,
    "total_retail_package_cost_sgd": null,
    "nutrients": {
      "calories_kcal": 779.0,
      "protein_g": 66.08,
      "carbs_g": 67.5,
      "fat_g": 27.67,
      "fiber_g": 10.0,
      "sugar_g": 0.0,
      "sodium_mg": 429.0,
      "saturated_fat_g": null,
      "cholesterol_mg": null
    },
    "nutrients_per_serving": {
      "calories_kcal": 389.5,
      "protein_g": 33.04,
      "carbs_g": 33.75,
      "fat_g": 13.84,
      "fiber_g": 5.0,
      "sugar_g": 0.0,
      "sodium_mg": 215.0,
      "saturated_fat_g": null,
      "cholesterol_mg": null
    }
  },
  "itemized": [
    {
      "ingredient": "Chicken Breast",
      "canonical_key": "chicken breast",
      "listing_name": "FarmFresh X Olagud RTE Chicken Breast (Peri Peri)",
      "retailer": "fairprice",
      "consumed_amount_g": 300.0,
      "consumed_cost_sgd": 7.87,
      "retail_package_cost_sgd": 9.44,
      "nutrients": {
        "calories_kcal": 429.0,
        "protein_g": 53.58,
        "carbs_g": 0.0,
        "fat_g": 21.42,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 429.0,
        "saturated_fat_g": null,
        "cholesterol_mg": 5.0
      },
      "warnings": [
        {
          "code": "PARTIAL_NUTRITION_DATA",
          "message": "Missing nutrients: saturated_fat_g"
        }
      ]
    },
    {
      "ingredient": "Rolled Oats",
      "canonical_key": "rolled oats",
      "listing_name": null,
      "retailer": null,
      "consumed_amount_g": 100.0,
      "consumed_cost_sgd": null,
      "retail_package_cost_sgd": null,
      "nutrients": {
        "calories_kcal": 350.0,
        "protein_g": 12.5,
        "carbs_g": 67.5,
        "fat_g": 6.25,
        "fiber_g": 10.0,
        "sugar_g": 0.0,
        "sodium_mg": 0.0,
        "saturated_fat_g": 0.0,
        "cholesterol_mg": null
      },
      "warnings": [
        {
          "code": "MISSING_PACKAGE_DATA",
          "message": "No cost-eligible fresh package was found"
        },
        {
          "code": "PARTIAL_NUTRITION_DATA",
          "message": "Missing nutrients: cholesterol_mg"
        }
      ]
    }
  ]
}

```

---

## 2. POST `/api/v1/plan`

Generates a feasible multi-day meal plan constrained by nutrients, dietary requirements, and
excluded allergens. Cost and budget do not gate plan eligibility.

### Request Parameters

| Field                  | Type            | In   | Nullable / Required     | Description                                                |
|------------------------|-----------------|------|-------------------------|------------------------------------------------------------|
| `horizon_days`         | `integer`       | Body | Required                | Planning duration in days (1 to 14).                       |
| `meals_per_day`        | `integer`       | Body | Required                | Meal slots per day (1 to 6).                               |
| `servings`             | `integer`       | Body | Optional (Default: `1`) | Number of servings per meal slot.                          |
| `nutrient_tolerance_pct` | `integer`     | Body | Optional (Default: `0`) | Nutrient-bound widening percentage (0 to 25).             |
| `allergies`            | `array[object]` | Body | Nullable                | Excluded allergens.                                        |
| `allergies[].code`     | `string`        | Body | Required                | Allergen identifier (e.g., `peanut`,shellfish`).           |
| `allergies[].severity` | `string`        | Body | Optional                | `mild` or `severe`.                                        |
| `dietary`              | `array[object]` | Body | Nullable                | Required dietary flags.                                    |
| `dietary[].code`       | `string`        | Body | Required                | Compliance identifier (`halal`, `vegetarian`).             |
| `nutrients`            | `array[object]` | Body | Nullable                | Targeted nutrient goals and boundaries.                    |
| `nutrients[].code`     | `string`        | Body | Required                | Nutrient key (`calories`, `protein`, `carbs`,fat`, etc.).  |
| `nutrients[].unit`     | `string`        | Body | Required                | Unit label (`kcal`, `g`, `mg`).                            |
| `nutrients[].goal`     | `object`        | Body | Nullable                | Target goal: `{"value": number}`.                          |
| `nutrients[].limit`    | `object`        | Body | Nullable                | Min/Max limits:`{"min": number, "max": number}`.           |

### Request Body Example

```json
{
  "horizon_days": 7,
  "meals_per_day": 3,
  "servings": 1,
  "nutrient_tolerance_pct": 10,
  "allergies": [
    {
      "code": "peanut",
      "severity": "severe"
    }
  ],
  "dietary": [
    {
      "code": "halal"
    }
  ],
  "nutrients": [
    {
      "code": "calories",
      "unit": "kcal",
      "goal": {
        "value": 2000
      },
      "limit": {
        "min": 1800,
        "max": 2200
      }
    },
    {
      "code": "protein",
      "unit": "g",
      "goal": {
        "value": 120
      },
      "limit": {
        "min": 100,
        "max": 140
      }
    }
  ]
}

```

### Response (`200 OK`)

`relaxed` is true only when the strict nutrient bounds were infeasible and the
requested widening produced a plan. In that case, `applied_tolerance_pct`
records the applied value and `status` is `partial`; otherwise the plan is
`complete` with tolerance `0`. Only nutrient `min` and `max` bounds widen. A
minimum is lowered and a maximum is raised by the requested percentage; goals
are unchanged. Recipe repetition limits and the no-consecutive-day rule are
never relaxed. The former structural-relaxation meaning of `partial` is removed.

The result includes plan-level feasibility, per-recipe outcomes, and
per-requirement constraint outcomes. A selected offer may be null when no
eligible offer exists; missing cost data does not drop a recipe. Offer
responses expose listing name and retailer. Audit provenance such as food keys,
source identifiers, mapping confidence, and normalization version is not part
of the user response.

```json
{
  "plan_id": "plan_99f2b8a01a",
  "status": "complete",
  "message": "Successfully generated a 1-day meal plan.",
  "validation_summary": {
    "allergen_status": "passed",
    "dietary_status": "not_requested"
  },
  "feasibility_outcome": "plan-produced",
  "relaxed": false,
  "applied_tolerance_pct": 0,
  "binding_constraints": null,
  "recipe_outcomes": [
    {
      "recipe_id": "recipe-101",
      "outcome": "selected",
      "cause": null,
      "causes": []
    }
  ],
  "constraint_outcomes": [
    {
      "recipe_id": "recipe-101",
      "requirement_text": "1 cup rolled oats",
      "constraint": "requirement",
      "state": "selected",
      "resolved_concept": "rolled oats",
      "selected_offer": {
        "listing_name": "Rolled Oats 1 kg",
        "retailer": "Example Market"
      },
      "warnings": []
    }
  ],
  "relaxations": [],
  "horizon_totals": {
    "avg_daily_calories": 450
  },
  "days": [
    {
      "day": 1,
      "meals": [
        {
          "slot": "meal_1",
          "recipe_id": "recipe-101",
          "title": "Rolled oats bowl",
          "instructions": "Combine and serve.",
          "nutrients": {
            "calories": 450
          },
          "ingredients": [
            {
              "quantity": 1,
              "unit": "cup",
              "text": "1 cup rolled oats",
              "preparation": null,
              "optional": false
            }
          ]
        }
      ]
    }
  ]
}
```

If no plan can satisfy the horizon after nutrient widening, the endpoint returns
`400 PLAN_INFEASIBLE` with the binding constraints in the error `details`. The
failure distinguishes an empty eligible pool (`no-recipes-survived`) from a
non-empty pool that cannot fill the horizon (`no-assignment`). If OR-Tools is
unavailable, the endpoint returns `503 SOLVER_UNAVAILABLE`; no degraded plan
is returned.

---

## 3. POST `/api/v1/chat` (SSE Streaming)

Handles interactive conversation, recipe adjustments, and follow-up Q&A via streaming events powered
by the LangGraph engine.

### Request Parameters

| Field          | Type     | In   | Nullable / Required | Description                                                   |
|----------------|----------|------|---------------------|---------------------------------------------------------------|
| `session_id`   | `string` | Body | Required            | Chat session UUID.                                            |
| `message`      | `string` | Body | Required            | User query string.                                            |
| `user_context` | `object` | Body | Nullable            | Active context values (e.g.,`{"current_plan_id": "string"}`). |

### Request Body Example

```json
{
  "session_id": "sess_88c0a21",
  "message": "Can you swap the lunch on Day 2 with a vegetarian alternative under $5?",
  "user_context": {
    "current_plan_id": "plan_99f2b8a01a"
  }
}

```

### Server-Sent Events Protocol

The HTTP stream sends plain text `event:` and `data:` blocks. In case of an error mid-stream, an
`event: error` frame is emitted before closing the connection.

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: metadata
data: {"session_id": "sess_88c0a21", "workflow_node": "ExtractConstraints"}

event: token
data: {"delta": "I can help with "}

event: token
data: {"delta": "that! Swapping Day 2 lunch to a Tofu Warm Bowl..."}

event: plan_updated
data: {"event": "plan_updated", "delta": {"day": 2, "slot": "meal_2", "recipe_id": "rec_tofu_04"}, "explanation": {"recipe": {"recipe_id": "rec_tofu_04", "outcome": "selected", "drop_causes": [], "constraints": [{"requirement_id": "req-tofu", "constraint": "vegetarian", "state": "pass", "resolved_concept": "tofu", "selected_offer": {"listing_name": "Firm tofu", "retailer": "Example Market"}, "warnings": []}]}, "constraints": [{"requirement_id": "req-tofu", "constraint": "vegetarian", "state": "pass", "resolved_concept": "tofu", "selected_offer": {"listing_name": "Firm tofu", "retailer": "Example Market"}, "warnings": []}]}}

event: error
data: {"code": "STREAM_INTERRUPTED", "message": "Downstream workflow timeout."}

event: done
data: {"status": "finished"}

```

---

## 4. POST `/api/v1/verify-dietary`

Verifies ingredients or recipes against explicit dietary compliance modes (halal, vegetarian) and
flags potential allergen conflicts.

### Request Parameters

| Field         | Type            | In   | Nullable / Required | Description                                                          |
|---------------|-----------------|------|---------------------|----------------------------------------------------------------------|
| `recipe_id`   | `string`        | Body | Required            | ID of the target recipe.                                             |
| `constraints` | `array[string]` | Body | Required            | Compliance rules to test (`"halal"`,`"vegetarian"`,`"peanut-free"`). |

### Request Body Example

```json
{
  "recipe_id": "rec_chicken_rice_01",
  "constraints": [
    "halal",
    "vegetarian"
  ]
}

```

### Response (`200 OK`)

```json
{
  "recipe_id": "rec_chicken_rice_01",
  "is_compliant": false,
  "status": "partial",
  "evaluations": [
    {
      "constraint": "vegetarian",
      "status": "failed",
      "reason": "Contains 'Chicken Breast' (meat product)"
    },
    {
      "constraint": "halal",
      "status": "verified",
      "reason": "Ingredients carry valid halal evidence sources"
    }
  ]
}

```

---

## 5. GET `/api/v1/recipes/{recipe_id}`

Retrieves normalized recipe data, preparation instructions, mapped FoodData Central profile
mappings, and available grocery product links.

### Request Parameters

| Field                 | Type      | In    | Nullable / Required         | Description                            |
|-----------------------|-----------|-------|-----------------------------|----------------------------------------|
| `recipe_id`           | `string`  | Path  | Required                    | Unique identifier for the recipe.      |
| `include_fulfillment` | `boolean` | Query | Optional (Default: `false`) | Include matched FairPrice retail SKUs. |

### Response (`200 OK`)

```json
{
  "recipe_id": "rec_oatmeal_01",
  "title": "High-Protein Overnight Oats",
  "instructions": [
    "Combine oats, chia seeds, and protein powder in a jar.",
    "Pour in milk and stir thoroughly.",
    "Refrigerate overnight."
  ],
  "required_food_concepts": [
    {
      "concept_name": "Rolled Oats",
      "quantity": 50,
      "unit": "g",
      "fdc_id": "173904",
      "fulfillment_offer": {
        "retailer": "FairPrice",
        "product_title": "FairPrice Whole Oats 800g",
        "price_sgd": 3.25
      }
    }
  ]
}

```

---

## 6. POST `/api/v1/recommendations/cold-start`

Serves baseline recommendations for unauthenticated or brand-new users before historical preference
context is established.

### Request Parameters

| Field                     | Type     | In   | Nullable / Required | Description                                                              |
|---------------------------|----------|------|---------------------|--------------------------------------------------------------------------|
| `dietary_preference`      | `string` | Body | Nullable            | Primary dietary preference filter (`"none"`, `"halal"`, `"vegetarian"`). |
| `target_daily_budget_sgd` | `number` | Body | Nullable            | Approximate target daily cost in SGD.                                    |

### Request Body Example

```json
{
  "dietary_preference": "none",
  "target_daily_budget_sgd": 12.00
}

```

### Response (`200 OK`)

```json
{
  "status": "success",
  "recommendations": [
    {
      "recipe_id": "rec_coldstart_01",
      "title": "Classic Egg & Avocado Toast",
      "estimated_cost_sgd": 2.50,
      "tags": [
        "quick",
        "budget-friendly"
      ]
    }
  ]
}

```

To implement client integration quickly, generate frontend API hooks or client SDKs directly using
FastAPI's auto-generated OpenAPI schema endpoint at `/openapi.json`.
