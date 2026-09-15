import AppShell from "@/components/app-shell";
import Plate from "@/components/plate";
import PromptConsole from "@/components/prompt-console";
import Shortlist from "@/components/shortlist";

export default function Page() {
  return (
    <AppShell>
      <div className="flex flex-wrap items-center gap-3">
        <p className="eyebrow">Your daily dose of delicious</p>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-sage px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-sage-foreground">
          <span className="size-1.5 rounded-full bg-sage-foreground/70" />
          Local demo
        </span>
      </div>

      <div className="mt-6 grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_23rem]">
        <div>
          <p className="eyebrow">The kind of helpful you can eat</p>
          <h1 className="mt-3 text-[2.75rem] font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
            Less overthinking.
            <br />
            <span className="text-accent">More good food.</span>
          </h1>
          <p className="mt-5 max-w-md leading-relaxed text-muted">
            A tiny nudge toward something delicious, tuned to your cravings,
            your time, and the ingredients you love.
          </p>
        </div>

        <Plate className="mx-auto w-full max-w-sm lg:max-w-none" />
      </div>

      <div className="mt-10">
        <PromptConsole />
      </div>

      <Shortlist />
    </AppShell>
  );
}
