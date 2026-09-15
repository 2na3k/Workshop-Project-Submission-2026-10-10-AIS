"use client";

import { useRouter } from "next/navigation";
import Field from "@/components/field";

export default function SignUpForm() {
  const router = useRouter();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: create the account, then hand off to the cold start. A brand new
    // account has no preference row yet, which is exactly what /welcome fills.
    router.push("/welcome");
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
        autoComplete="new-password"
        placeholder="At least 8 characters"
      />

      <button
        type="submit"
        className="w-full rounded-full bg-accent px-4 py-3 text-sm font-bold text-accent-foreground transition hover:opacity-90"
      >
        Create account
      </button>

      <p className="text-center text-xs leading-relaxed text-muted">
        Next we&rsquo;ll ask three quick questions so your first suggestions
        actually fit.
      </p>
    </form>
  );
}
