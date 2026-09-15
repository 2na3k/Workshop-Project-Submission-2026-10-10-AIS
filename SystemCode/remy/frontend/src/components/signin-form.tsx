"use client";

import { useRouter } from "next/navigation";
import Field from "@/components/field";

export default function SignInForm() {
  const router = useRouter();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: authenticate with new FormData(event.currentTarget), then land the
    // user on Discover. Returning users already have preferences, so no cold
    // start here - that belongs to sign up only.
    router.push("/");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field
        id="username"
        label="Username"
        autoComplete="username"
        placeholder="yourname"
      />
      <Field
        id="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        placeholder="••••••••"
      />

      <button
        type="submit"
        className="w-full rounded-full bg-accent px-4 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90"
      >
        Sign in
      </button>
    </form>
  );
}
