"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Field from "@/components/field";
import FormError from "@/components/form-error";
import { ApiError, signIn } from "@/lib/api";

export default function SignInForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);

    setError(null);
    setPending(true);

    try {
      await signIn({
        username: String(data.get("username") ?? ""),
        password: String(data.get("password") ?? ""),
      });
      // Returning users already have a preference row, so no cold start.
      router.push("/");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Something went wrong.",
      );
      // Only on failure: on success the route change unmounts this form, and
      // clearing pending first would flash the button back to its idle label.
      setPending(false);
    }
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

      <FormError message={error} />

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-full bg-accent px-4 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
