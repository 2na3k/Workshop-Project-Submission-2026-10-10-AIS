import Logo from "@/components/logo";

/** Centred shell for the pages you see before entering the app. */
export default function Screen({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-dvh items-center justify-center px-5 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo />
          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-balance">
            {title}
          </h1>
          <p className="mt-2.5 text-sm leading-relaxed text-muted text-balance">
            {subtitle}
          </p>
        </div>

        <div className="rounded-3xl border border-subtle bg-surface p-6 shadow-[0_1px_2px_rgba(33,56,42,0.04),0_12px_32px_-12px_rgba(33,56,42,0.12)] sm:p-7">
          {children}
        </div>
      </div>
    </main>
  );
}
