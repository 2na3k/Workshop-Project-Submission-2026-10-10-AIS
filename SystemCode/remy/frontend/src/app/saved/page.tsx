import type { Metadata } from "next";
import AppShell from "@/components/app-shell";
import { Heart } from "@/components/icons";

export const metadata: Metadata = {
  title: "Saved meals · Remy",
  description: "The meals you kept for later.",
};

export default function Page() {
  return (
    <AppShell>
      <p className="eyebrow">Kept for later</p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tight">
        Saved meals
      </h1>

      <div className="mt-8 rounded-3xl border border-dashed border-subtle bg-surface/60 px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-cream text-muted">
          <Heart className="size-7" />
        </span>
        <p className="mt-4 font-bold">Nothing saved yet</p>
        <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted">
          Tap the heart on any idea and it will wait for you here, ready for the
          next time you cannot decide.
        </p>
      </div>
    </AppShell>
  );
}
