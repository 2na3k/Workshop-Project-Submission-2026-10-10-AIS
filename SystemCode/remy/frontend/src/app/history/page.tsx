import type { Metadata } from "next";
import AppShell from "@/components/app-shell";
import { Clock } from "@/components/icons";

export const metadata: Metadata = {
  title: "History · Remy",
  description: "The meals you have already explored together.",
};

export default function Page() {
  return (
    <AppShell>
      <p className="eyebrow">Where you have been</p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tight">History</h1>

      <div className="mt-8 rounded-3xl border border-dashed border-subtle bg-surface/60 px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-cream text-muted">
          <Clock className="size-7" />
        </span>
        <p className="mt-4 font-bold">Nothing here yet</p>
        <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted">
          Meals you have already seen will show up here, so you can always look
          back at what you explored.
        </p>
      </div>
    </AppShell>
  );
}
