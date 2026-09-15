"use client";

import { useState } from "react";
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

/** The in-app editor. Same options as the cold start, but all on one page:
 *  someone changing a setting does not want a wizard. */
export default function PreferencesForm() {
  const router = useRouter();
  const [prefs, setPrefs] = useState<Preferences>(EMPTY_PREFERENCES);

  function toggleCuisine(cuisine: string) {
    setPrefs((current) => ({
      ...current,
      cuisines: current.cuisines.includes(cuisine)
        ? current.cuisines.filter((item) => item !== cuisine)
        : [...current.cuisines, cuisine],
    }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: PUT prefs to the preference table for the signed-in user.
    router.push("/");
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-6">
      <fieldset className="rounded-3xl border border-subtle bg-surface p-6">
        <legend className="float-left w-full text-sm font-bold">Diet</legend>
        <p className="clear-both text-sm text-muted">Pick the one that fits you.</p>

        <div className="mt-4 grid gap-2.5 sm:grid-cols-3">
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
              <span className="mt-1 block text-sm leading-snug text-muted">
                {hint}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="rounded-3xl border border-subtle bg-surface p-6">
        <legend className="float-left w-full text-sm font-bold">Cuisines</legend>
        <p className="clear-both text-sm text-muted">
          Choose as many as you like, or skip and we&rsquo;ll suggest broadly.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {CUISINES.map((cuisine) => (
            <Chip
              key={cuisine}
              label={cuisine}
              selected={prefs.cuisines.includes(cuisine)}
              onClick={() => toggleCuisine(cuisine)}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="rounded-3xl border border-subtle bg-surface p-6">
        <legend className="float-left w-full text-sm font-bold">Aim for</legend>
        <p className="clear-both text-sm text-muted">
          One nutrient to steer suggestions by.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
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
      </fieldset>

      <button
        type="submit"
        disabled={prefs.diet === null}
        className="rounded-full bg-accent px-6 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Save preferences
      </button>
    </form>
  );
}
