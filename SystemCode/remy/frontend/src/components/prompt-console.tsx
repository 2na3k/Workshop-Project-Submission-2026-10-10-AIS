"use client";

import { useState } from "react";
import { ArrowUp, Bubble, Sparkle } from "@/components/icons";

const STARTERS = ["Ready in 20", "Plant-powered", "Protein please", "Surprise me"];
const REFINEMENTS = ["Make it quicker", "No dairy", "More protein"];

type Message = { id: number; from: "you" | "remy"; text: string };

export default function PromptConsole() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const trimmed = draft.trim();

  function send(text: string) {
    const value = text.trim();
    if (!value) return;

    // TODO: replace the canned reply with the recommender response.
    setMessages((current) => [
      ...current,
      { id: current.length, from: "you", text: value },
      {
        id: current.length + 1,
        from: "remy",
        text: "I found 6 ideas that fit. Want to nudge the vibe?",
      },
    ]);
    setDraft("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(draft);
    }
  }

  return (
    <section>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          send(draft);
        }}
        className="rounded-3xl border border-subtle bg-surface p-5 shadow-[0_1px_2px_rgba(33,56,42,0.04),0_12px_32px_-12px_rgba(33,56,42,0.12)] sm:p-6"
      >
        <p className="mb-3 flex items-center gap-2 text-sm font-bold">
          <Sparkle className="size-[1.15rem] text-accent" />
          Tell me what sounds good
        </p>

        <div className="flex items-start gap-3">
          <label htmlFor="prompt" className="sr-only">
            What sounds good?
          </label>
          <textarea
            id="prompt"
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Something quick, filling, and a little spicy…"
            className="min-w-0 flex-1 resize-none bg-transparent text-lg leading-relaxed outline-none placeholder:text-muted/70 sm:text-xl"
          />

          <button
            type="submit"
            disabled={!trimmed}
            aria-label="Send"
            className={`grid size-11 shrink-0 place-items-center rounded-full transition ${
              trimmed
                ? "bg-accent text-accent-foreground hover:opacity-90"
                : "bg-cream text-muted/50"
            }`}
          >
            <ArrowUp className="size-5" />
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {STARTERS.map((starter) => (
            <button
              key={starter}
              type="button"
              onClick={() => send(starter)}
              className="rounded-full border border-subtle px-3.5 py-1.5 text-sm text-muted transition hover:border-sage-deep hover:text-foreground"
            >
              {starter}
            </button>
          ))}
        </div>
      </form>

      {messages.length > 0 && (
        <>
          <div className="mt-8 space-y-3">
            {messages.map((message) =>
              message.from === "you" ? (
                <p
                  key={message.id}
                  className="ml-auto w-fit max-w-[80%] rounded-2xl bg-sage px-4 py-2.5 text-sm text-sage-foreground"
                >
                  {message.text}
                </p>
              ) : (
                <p
                  key={message.id}
                  className="flex w-fit max-w-[85%] items-center gap-2.5 rounded-2xl border border-subtle bg-surface px-4 py-2.5 text-sm"
                >
                  <Bubble className="size-[1.15rem] shrink-0 text-muted" />
                  {message.text}
                </p>
              ),
            )}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted">Refine it</span>
            {REFINEMENTS.map((refinement) => (
              <button
                key={refinement}
                type="button"
                onClick={() => send(refinement)}
                className="rounded-full bg-sage px-3.5 py-1.5 text-sm font-medium text-sage-foreground transition hover:bg-sage-deep"
              >
                {refinement}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
