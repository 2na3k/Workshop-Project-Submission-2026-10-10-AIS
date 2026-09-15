import Link from "next/link";

/** Entry points to the auth screens. Always visible for now: there is no
 *  session yet, so the app cannot tell whether anyone is signed in. Once
 *  sign in returns a token, this should swap for an account menu. */
export default function AuthButtons() {
  return (
    <div className="mb-7 flex items-center justify-end gap-2">
      <Link
        href="/signin"
        className="rounded-full border border-subtle px-4 py-2 text-sm font-semibold text-muted transition hover:border-sage-deep hover:text-foreground"
      >
        Sign in
      </Link>
      <Link
        href="/signup"
        className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-accent-foreground transition hover:opacity-90"
      >
        Sign up
      </Link>
    </div>
  );
}
