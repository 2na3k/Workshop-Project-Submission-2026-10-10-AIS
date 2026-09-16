/** Where the bearer token lives between page loads.
 *
 *  localStorage is readable by any script on the page, so an XSS bug would
 *  expose the token. The safer arrangement is an httpOnly cookie set by the
 *  backend, which JavaScript cannot read at all - worth moving to before this
 *  handles anything real.
 *
 *  Every access is wrapped: localStorage throws outright in some contexts
 *  (Safari private mode, embedded webviews, site data blocked). */

const KEY = "remy.session";

export type Session = {
  username: string;
  accessToken: string;
  expiresAt: number;
};

export function saveSession(session: Session): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // Not fatal: the session lasts until the tab closes instead of persisting.
  }
}

export function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as Partial<Session>;
    if (typeof parsed.accessToken !== "string" || !parsed.accessToken) {
      return null;
    }
    return {
      username: String(parsed.username ?? ""),
      accessToken: parsed.accessToken,
      expiresAt: Number(parsed.expiresAt ?? 0),
    };
  } catch {
    return null;
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Nothing to do - a token we cannot reach is a token we cannot send.
  }
}
