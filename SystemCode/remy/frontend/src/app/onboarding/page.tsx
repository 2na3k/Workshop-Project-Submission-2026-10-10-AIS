import type { Metadata } from "next";
import AppShell from "@/components/app-shell";
import PreferencesForm from "@/components/preferences-form";

export const metadata: Metadata = {
  title: "Your preferences · Remy",
  description: "Tell Remy about your diet and the cuisines you enjoy.",
};

export default function Page() {
  return (
    <AppShell>
      <p className="eyebrow">So we suggest the right things</p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tight">
        What do you eat?
      </h1>
      <p className="mt-3 max-w-md leading-relaxed text-muted">
        This shapes every idea Remy suggests. You can change it whenever you
        like.
      </p>

      <PreferencesForm />
    </AppShell>
  );
}
