/** Client for the FastAPI backend in ../../backend. */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type Credentials = { username: string; password: string };
export type Account = { username: string };

/** FastAPI returns `detail` as a string for HTTPException and as a list of
 *  `{loc, msg}` for request validation errors. Flatten both to one line. */
function messageFrom(payload: unknown, status: number): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    if (typeof first?.msg === "string") return first.msg;
  }

  return `Something went wrong (${status}).`;
}

async function post<T>(path: string, body: Credentials): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    // fetch only rejects when the request never completed: backend down, wrong
    // port, CORS preflight refused. Status 0 marks "no response at all".
    throw new ApiError(
      "Cannot reach the server. Is the backend running on " + API_URL + "?",
      0,
    );
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(messageFrom(payload, response.status), response.status);
  }

  return payload as T;
}

export const signUp = (credentials: Credentials) =>
  post<Account>("/auth/signup", credentials);

export const signIn = (credentials: Credentials) =>
  post<Account>("/auth/signin", credentials);
