/** Client for the FastAPI backend in ../../backend. */

import { clearSession, readSession, saveSession } from "@/lib/session";

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

/** Wire shape of the preference row; snake_case to match the API. */
export type PreferencesPayload = {
  special_diet: string | null;
  cuisines: string[];
  preferred_nutrient: string | null;
};

type SessionResponse = {
  username: string;
  access_token: string;
  token_type: string;
  expires_at: number;
};

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

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only rejects when the request never completed: backend down, wrong
    // port, CORS preflight refused. Status 0 marks "no response at all".
    throw new ApiError(
      `Cannot reach the server. Is the backend running on ${API_URL}?`,
      0,
    );
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    // A rejected token is worse than useless - drop it so the next screen can
    // send the user back to sign in rather than retrying with a dead one.
    if (response.status === 401 && token) clearSession();
    throw new ApiError(messageFrom(payload, response.status), response.status);
  }

  return payload as T;
}

function keepSession(response: SessionResponse): SessionResponse {
  saveSession({
    username: response.username,
    accessToken: response.access_token,
    expiresAt: response.expires_at,
  });
  return response;
}

export async function signUp(credentials: Credentials) {
  return keepSession(
    await request<SessionResponse>("POST", "/auth/signup", credentials),
  );
}

export async function signIn(credentials: Credentials) {
  return keepSession(
    await request<SessionResponse>("POST", "/auth/signin", credentials),
  );
}

function requireToken(): string {
  const session = readSession();
  if (!session) {
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }
  return session.accessToken;
}

export const savePreferences = (preferences: PreferencesPayload) =>
  request<PreferencesPayload & { username: string }>(
    "PUT",
    "/preferences",
    preferences,
    requireToken(),
  );

/** Resolves to null when nothing has been saved yet (the backend 404s). */
export async function loadPreferences(): Promise<PreferencesPayload | null> {
  try {
    return await request<PreferencesPayload>(
      "GET",
      "/preferences",
      undefined,
      requireToken(),
    );
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) return null;
    throw caught;
  }
}
