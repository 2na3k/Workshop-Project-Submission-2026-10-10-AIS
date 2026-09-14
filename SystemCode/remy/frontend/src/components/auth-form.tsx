"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Field from "@/components/field";

type Mode = "signin" | "signup";

export default function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const isSignUp = mode === "signup";

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: call the auth endpoint with new FormData(event.currentTarget).
    // Existing users would go straight to /prompt once that lands.
    router.push("/onboarding");
  }

  return (
    <>
      <div
        role="tablist"
        aria-label="Authentication mode"
        className="mb-6 grid grid-cols-2 gap-1 rounded-lg bg-background p-1"
      >
        {(["signin", "signup"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={mode === value}
            onClick={() => setMode(value)}
            className={`rounded-md px-3 py-2 text-sm font-medium transition ${
              mode === value
                ? "bg-surface text-foreground shadow-sm"
                : "text-muted hover:text-foreground"
            }`}
          >
            {value === "signin" ? "Sign in" : "Sign up"}
          </button>
        ))}
      </div>

      {/* Remounting on mode change clears whatever the other mode had typed. */}
      <form key={mode} onSubmit={handleSubmit} className="space-y-4">
        {isSignUp && (
          <Field
            id="name"
            label="Name"
            autoComplete="name"
            placeholder="Remy Ratatouille"
          />
        )}

        <Field
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
        />

        <Field
          id="password"
          label="Password"
          type="password"
          autoComplete={isSignUp ? "new-password" : "current-password"}
          placeholder="••••••••"
        />

        <button
          type="submit"
          className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-accent/40"
        >
          {isSignUp ? "Create account" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        {isSignUp ? "Already cooking with us?" : "New here?"}{" "}
        <button
          type="button"
          onClick={() => setMode(isSignUp ? "signin" : "signup")}
          className="font-medium text-accent underline-offset-4 hover:underline"
        >
          {isSignUp ? "Sign in" : "Create an account"}
        </button>
      </p>
    </>
  );
}
