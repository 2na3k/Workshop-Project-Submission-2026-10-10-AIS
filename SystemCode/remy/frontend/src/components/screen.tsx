/** Centred card shell shared by every screen in the onboarding flow. */
export default function Screen({
  title,
  subtitle,
  width = "narrow",
  children,
}: {
  title: string;
  subtitle: string;
  width?: "narrow" | "wide";
  children: React.ReactNode;
}) {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-10">
      <div className={width === "wide" ? "w-full max-w-2xl" : "w-full max-w-md"}>
        <header className="mb-8 text-center">
          <p className="text-sm font-semibold tracking-[0.2em] text-accent uppercase">
            Remy
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance">
            {title}
          </h1>
          <p className="mt-2 text-sm text-muted text-balance">{subtitle}</p>
        </header>

        <div className="rounded-2xl border border-subtle bg-surface p-6 shadow-sm sm:p-8">
          {children}
        </div>
      </div>
    </main>
  );
}
