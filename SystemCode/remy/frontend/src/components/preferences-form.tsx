"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

/** Mutually exclusive: "vegetarian" and "meat" contradict each other. */
const DIETS = [
  { id: "halal", label: "Halal", hint: "Halal-certified ingredients only" },
  { id: "vegetarian", label: "Vegetarian", hint: "No meat or seafood" },
  { id: "meat", label: "Meat", hint: "Anything goes" },
] as const;

const CUISINES = [
  "Chinese",
  "Malay",
  "Indian",
  "Peranakan",
  "Thai",
  "Vietnamese",
  "Japanese",
  "Korean",
  "Western",
  "Italian",
  "Mexican",
  "Middle Eastern",
] as const;

type Diet = (typeof DIETS)[number]["id"];

export default function PreferencesForm() {
  const router = useRouter();
  const [diet, setDiet] = useState<Diet | null>(null);
  const [cuisines, setCuisines] = useState<string[]>([]);

  function toggleCuisine(cuisine: string) {
    setCuisines((current) =>
      current.includes(cuisine)
        ? current.filter((item) => item !== cuisine)
        : [...current, cuisine],
    );
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: persist { diet, cuisines } against the signed-in user.
    router.push("/prompt");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <fieldset>
        <legend className="text-sm font-medium">Diet</legend>
        <p className="mt-1 text-sm text-muted">Pick the one that fits you.</p>

        <div className="mt-3 space-y-2">
          {DIETS.map(({ id, label, hint }) => (
            <label
              key={id}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                diet === id
                  ? "border-accent bg-accent/5"
                  : "border-subtle hover:border-muted/40"
              }`}
            >
              <input
                type="radio"
                name="diet"
                value={id}
                checked={diet === id}
                onChange={() => setDiet(id)}
                className="mt-0.5 size-4 accent-accent"
              />
              <span>
                <span className="block text-sm font-medium">{label}</span>
                <span className="block text-sm text-muted">{hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="text-sm font-medium">Cuisines</legend>
        <p className="mt-1 text-sm text-muted">
          Choose as many as you like, or skip and we&rsquo;ll suggest broadly.
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
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
                    ? "border-accent bg-accent text-accent-foreground"
                    : "border-subtle text-muted hover:border-muted/40 hover:text-foreground"
                }`}
              >
                {cuisine}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="flex items-center justify-between gap-4 border-t border-subtle pt-6">
        <Link
          href="/signin"
          className="text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
        >
          Back
        </Link>

        <button
          type="submit"
          disabled={diet === null}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Continue
        </button>
      </div>
    </form>
  );
}
