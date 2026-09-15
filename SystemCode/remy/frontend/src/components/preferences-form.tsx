"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/** Mutually exclusive: "vegetarian" and "meat" contradict each other. */
const DIETS = [
  { id: "halal", label: "Halal", hint: "Halal-certified ingredients only" },
  { id: "vegetarian", label: "Vegetarian", hint: "No meat or seafood" },
  { id: "meat", label: "Meat", hint: "Anything goes" },
] as const;

const CUISINES = [
  "Chinese", "Malay", "Indian", "Peranakan", "Thai", "Vietnamese",
  "Japanese", "Korean", "Western", "Italian", "Mexican", "Middle Eastern",
] as const;

const NUTRIENTS = ["Protein", "Fibre", "Lower sodium", "Lower sugar"] as const;

type Diet = (typeof DIETS)[number]["id"];

export default function PreferencesForm() {
  const router = useRouter();
  const [diet, setDiet] = useState<Diet | null>(null);
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [nutrient, setNutrient] = useState<string | null>(null);

  function toggleCuisine(cuisine: string) {
    setCuisines((current) =>
      current.includes(cuisine)
        ? current.filter((item) => item !== cuisine)
        : [...current, cuisine],
    );
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: PUT { diet, cuisines, nutrient } to the preference table.
    router.push("/");
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-8">
      <fieldset className="rounded-3xl border border-subtle bg-surface p-6">
        <legend className="float-left w-full text-sm font-bold">Diet</legend>
        <p className="clear-both text-sm text-muted">Pick the one that fits you.</p>

        <div className="mt-4 grid gap-2.5 sm:grid-cols-3">
          {DIETS.map(({ id, label, hint }) => (
            <label
              key={id}
              className={`cursor-pointer rounded-2xl border p-4 transition ${
                diet === id
                  ? "border-accent bg-accent/5"
                  : "border-subtle hover:border-sage-deep"
              }`}
            >
              <input
                type="radio"
                name="diet"
                value={id}
                checked={diet === id}
                onChange={() => setDiet(id)}
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
          {CUISINES.map((cuisine) => {
            const selected = cuisines.includes(cuisine);
            return (
              <button
                key={cuisine}
                type="button"
                aria-pressed={selected}
                onClick={() => toggleCuisine(cuisine)}
                className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
                  selected
                    ? "border-sage-deep bg-sage font-medium text-sage-foreground"
                    : "border-subtle text-muted hover:border-sage-deep hover:text-foreground"
                }`}
              >
                {cuisine}
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="rounded-3xl border border-subtle bg-surface p-6">
        <legend className="float-left w-full text-sm font-bold">Aim for</legend>
        <p className="clear-both text-sm text-muted">One nutrient to steer suggestions by.</p>

        <div className="mt-4 flex flex-wrap gap-2">
          {NUTRIENTS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={nutrient === option}
              onClick={() => setNutrient(nutrient === option ? null : option)}
              className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
                nutrient === option
                  ? "border-sage-deep bg-sage font-medium text-sage-foreground"
                  : "border-subtle text-muted hover:border-sage-deep hover:text-foreground"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={diet === null}
        className="rounded-full bg-accent px-6 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Save preferences
      </button>
    </form>
  );
}
