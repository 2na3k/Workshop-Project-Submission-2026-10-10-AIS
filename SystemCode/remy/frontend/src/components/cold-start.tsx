"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Chip from "@/components/chip";
import {
  CUISINES,
  DIETS,
  EMPTY_PREFERENCES,
  NUTRIENTS,
  type Diet,
  type Preferences,
} from "@/components/preference-options";

const STEPS = [
  { key: "diet", question: "Any dietary needs?", hint: "Pick the one that fits you." },
  { key: "cuisines", question: "Which cuisines do you love?", hint: "Choose as many as you like." },
  { key: "nutrient", question: "Anything you're aiming for?", hint: "One nutrient to steer suggestions by." },
] as const;

export default function ColdStart() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState<Preferences>(EMPTY_PREFERENCES);

  const isLast = step === STEPS.length - 1;
  // Only the diet step blocks progress; the other two are genuinely optional.
  const canAdvance = step !== 0 || prefs.diet !== null;

  function finish() {
    // TODO: POST prefs to the preference table for the new account.
    router.push("/");
  }

  function toggleCuisine(cuisine: string) {
    setPrefs((current) => ({
      ...current,
      cuisines: current.cuisines.includes(cuisine)
        ? current.cuisines.filter((item) => item !== cuisine)
        : [...current.cuisines, cuisine],
    }));
  }

  return (
    <div className="w-full max-w-lg">
      <div className="flex items-center gap-3">
        {STEPS.map((item, index) => (
          <span
            key={item.key}
            className={`h-1.5 flex-1 rounded-full transition ${
              index <= step ? "bg-accent" : "bg-subtle"
            }`}
          />
        ))}
      </div>

      <p className="eyebrow mt-5">
        Step {step + 1} of {STEPS.length}
      </p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-balance sm:text-4xl">
        {STEPS[step].question}
      </h1>
      <p className="mt-2 text-sm text-muted">{STEPS[step].hint}</p>

      <div className="mt-7 rounded-3xl border border-subtle bg-surface p-6">
        {step === 0 && (
          <div className="grid gap-2.5">
            {DIETS.map(({ id, label, hint }) => (
              <label
                key={id}
                className={`cursor-pointer rounded-2xl border p-4 transition ${
                  prefs.diet === id
                    ? "border-accent bg-accent/5"
                    : "border-subtle hover:border-sage-deep"
                }`}
              >
                <input
                  type="radio"
                  name="diet"
                  value={id}
                  checked={prefs.diet === id}
                  onChange={() =>
                    setPrefs((current) => ({ ...current, diet: id as Diet }))
                  }
                  className="sr-only"
                />
                <span className="block font-bold">{label}</span>
                <span className="mt-1 block text-sm text-muted">{hint}</span>
              </label>
            ))}
          </div>
        )}

        {step === 1 && (
          <div className="flex flex-wrap gap-2">
            {CUISINES.map((cuisine) => (
              <Chip
                key={cuisine}
                label={cuisine}
                selected={prefs.cuisines.includes(cuisine)}
                onClick={() => toggleCuisine(cuisine)}
              />
            ))}
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-wrap gap-2">
            {NUTRIENTS.map((option) => (
              <Chip
                key={option}
                label={option}
                selected={prefs.nutrient === option}
                onClick={() =>
                  setPrefs((current) => ({
                    ...current,
                    nutrient: current.nutrient === option ? null : option,
                  }))
                }
              />
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between gap-4">
        {step === 0 ? (
          <Link
            href="/signup"
            className="text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
          >
            Back
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => setStep((current) => current - 1)}
            className="text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
          >
            Back
          </button>
        )}

        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={finish}
            className="text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
          >
            Skip for now
          </button>

          <button
            type="button"
            disabled={!canAdvance}
            onClick={() => (isLast ? finish() : setStep((c) => c + 1))}
            className="rounded-full bg-accent px-6 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isLast ? "Start cooking" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
