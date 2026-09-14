"use client";

import { useState } from "react";

export default function PromptBox() {
  const [prompt, setPrompt] = useState("");
  const trimmed = prompt.trim();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmed) return;
    // TODO: send `trimmed` to the recommender and render the results.
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl+Enter submits without leaving the textarea.
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="prompt" className="sr-only">
        What would you like to cook?
      </label>
      <textarea
        id="prompt"
        name="prompt"
        rows={5}
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Something quick with chicken and whatever is cheap this week..."
        className="w-full resize-none rounded-lg border border-subtle bg-background px-3.5 py-3 text-sm leading-relaxed outline-none transition placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/25"
      />

      <div className="mt-4 flex items-center justify-between gap-4">
        <p className="text-xs text-muted">
          <kbd className="font-mono">⌘</kbd>
          <kbd className="font-mono">↵</kbd> to send
        </p>

        <button
          type="submit"
          disabled={!trimmed}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask Remy
        </button>
      </div>
    </form>
  );
}
