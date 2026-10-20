import type { PlanIngredient } from "./plan-api";

export type ChatMetadata = {
  session_id: string;
  workflow_node: string;
  trace_id: string;
};

export type ChatMealContent = {
  title: string;
  nutrients: Record<string, number>;
  ingredients: PlanIngredient[];
  instructions: string | null;
};

export type ChatPlanUpdate = {
  delta: { day: number; slot: string; recipe_id: string };
  explanation: {
    recipe: {
      recipe_id: string;
      outcome: string;
      drop_causes: string[];
      constraints: unknown[];
      meal: ChatMealContent | null;
    };
    constraints: unknown[];
  };
};

export type ChatEvent =
  | { type: "metadata"; data: ChatMetadata }
  | { type: "token"; text: string }
  | { type: "plan_updated"; data: ChatPlanUpdate }
  | { type: "done"; status: string; trace_id: string }
  | { type: "error"; code: string; message: string };

export async function* streamChat(
    sessionId: string,
    message: string,
    userContext?: unknown,
): AsyncGenerator<ChatEvent> {
  const REMY_API_URL = process.env.NEXT_PUBLIC_REMY_API_URL ?? "http://localhost:8081";

  let response: Response;
  try {
    response = await fetch(`${REMY_API_URL}/api/v1/chat`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ session_id: sessionId, message, user_context: userContext ?? null }),
    });
  } catch {
    throw new Error("Cannot reach the chat service. Please try again.");
  }

  if (!response.ok || !response.body) {
    throw new Error("The chat service is unavailable. Please try again.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2); // Move past the \n\n

        let event = "message";
        const dataLines: string[] = [];

        for (const line of block.split("\n")) {
          if (line.startsWith(":")) continue; // Skip : ping heartbeats
          const colon = line.indexOf(":");
          const field = colon === -1 ? line : line.slice(0, colon);
          const val = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");

          if (field === "event") event = val;
          if (field === "data") dataLines.push(val);
        }

        // Only yield if there's actual data (ignore the empty keep-alive block)
        if (dataLines.length > 0) {
          let payload: unknown;
          try {
            payload = JSON.parse(dataLines.join("\n"));
          } catch {
            // Skip malformed data
            boundary = buffer.indexOf("\n\n");
            continue;
          }

          if (event === "metadata") {
            yield { type: "metadata", data: payload as ChatMetadata };
          } else if (event === "token") {
            const delta = (payload as { delta?: unknown }).delta;
            yield { type: "token", text: typeof delta === "string" ? delta : "" };
          } else if (event === "plan_updated") {
            yield { type: "plan_updated", data: payload as ChatPlanUpdate };
          } else if (event === "done") {
            const p = payload as { status?: unknown; trace_id?: unknown };
            yield { type: "done", status: String(p.status ?? ""), trace_id: String(p.trace_id ?? "") };
          } else if (event === "error") {
            const p = payload as { code?: unknown; message?: unknown };
            yield { type: "error", code: String(p.code ?? "ERROR"), message: String(p.message ?? "Unknown error") };
          }
        }

        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
