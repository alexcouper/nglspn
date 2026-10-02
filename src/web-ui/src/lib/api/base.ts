import type { components } from "../api-types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ApiError = components["schemas"]["Error"];

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public body: Record<string, unknown>,
    public status: number,
  ) {
    super(message);
  }
}

// The refresh outcome matters to callers, not only to this file. "transient"
// means the credentials are still good and a retry will work; "invalid" means
// the session is over and the redirect to /login is already in flight. Callers
// that tell a person what happened must be able to tell the two apart by type —
// a string match on the message would not survive the first reword.
//
// The messages are unchanged. They are for whoever is reading the console.
export class AuthTransientError extends Error {
  constructor() {
    super("Token refresh failed");
  }
}

export class AuthExpiredError extends Error {
  constructor() {
    super("Unauthorized");
  }
}

type RefreshOutcome = "refreshed" | "invalid" | "transient";

// Who the session belongs to, remembered across reloads. A refresh must never
// change the answer: the refresh cookie is set by the API host and a forged
// cross-site login could plant someone else's, so a refresh that comes back as
// another user is treated as the session ending, not as a new session.
const SESSION_USER_KEY = "session_user_id";

// The `user_id` claim of an access token, read without checking the signature.
// The backend verifies tokens; this only reads who the token says it is for.
function userIdOf(accessToken: string): string | null {
  try {
    const payload = accessToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(atob(payload));
    return typeof claims.user_id === "string" ? claims.user_id : null;
  } catch {
    return null;
  }
}

export class APIClient {
  private accessToken: string | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<RefreshOutcome> | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      // The refresh token is an HttpOnly cookie on the API host; script never
      // sees it. Builds before the cookie kept it here, and that copy is a
      // long-lived credential readable by any script, so it goes.
      localStorage.removeItem("refresh_token");
    }
  }

  // After a login. The refresh token arrived as a cookie on the same response.
  setSession(access: string) {
    this.setAccessToken(access);
    if (typeof window !== "undefined") {
      this.rememberSessionUser(access);
      document.cookie = "logged_in=true; path=/; SameSite=Lax";
    }
  }

  private rememberSessionUser(access: string) {
    const userId = userIdOf(access);
    if (userId) {
      localStorage.setItem(SESSION_USER_KEY, userId);
    }
  }

  // True when `access` is for someone other than the remembered session user.
  // With nothing remembered (first login, or storage purged) any user is fine.
  private isSessionUserChange(access: string): boolean {
    const known = localStorage.getItem(SESSION_USER_KEY);
    return known !== null && userIdOf(access) !== known;
  }

  private setAccessToken(access: string) {
    this.accessToken = access;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access);
    }
  }

  clearTokens() {
    this.accessToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem(SESSION_USER_KEY);
      document.cookie = "logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
    }
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // Holding no access token does not mean there is no session: the refresh
  // cookie is invisible to script and outlives localStorage (Safari purges the
  // latter after seven days without a visit). Asking is the only way to know.
  async refreshSession(): Promise<void> {
    const outcome = await this.attemptTokenRefresh();
    if (outcome === "invalid") {
      throw new AuthExpiredError();
    }
    if (outcome === "transient") {
      throw new AuthTransientError();
    }
  }

  private async attemptTokenRefresh(): Promise<RefreshOutcome> {
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = (async (): Promise<RefreshOutcome> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
          method: "POST",
          // Sends the refresh cookie and lets the response replace it.
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        // Only the backend can say the session is over. Anything else leaves
        // the cookie where it is, to be tried again.
        if (response.status === 401) {
          return "invalid";
        }

        if (!response.ok) {
          return "transient";
        }

        const data = await response.json();
        if (typeof window !== "undefined" && this.isSessionUserChange(data.access_token)) {
          // The cookie is not ours. Get rid of it and end the session.
          fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
          }).catch(() => {});
          return "invalid";
        }
        this.setAccessToken(data.access_token);
        if (typeof window !== "undefined") {
          this.rememberSessionUser(data.access_token);
          window.dispatchEvent(new Event("auth:refreshed"));
        }
        return "refreshed";
      } catch {
        return "transient";
      } finally {
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isRetry: boolean = false
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (this.accessToken) {
      (headers as Record<string, string>)["Authorization"] =
        `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && !isRetry) {
      const outcome = await this.attemptTokenRefresh();

      if (outcome === "refreshed") {
        return this.request<T>(endpoint, options, true);
      }

      if (outcome === "invalid") {
        this.clearTokens();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("auth:logout"));
        }
        throw new AuthExpiredError();
      }

      // transient: refresh request failed for non-credential reasons
      // (network blip, 5xx, rate limit). Keep tokens so the user stays
      // logged in once connectivity / the backend recovers.
      throw new AuthTransientError();
    }

    if (response.status === 401) {
      this.clearTokens();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("auth:logout"));
      }
      throw new AuthExpiredError();
    }

    if (!response.ok) {
      // A 502 from the proxy is an HTML page, and an unguarded json() would
      // throw a SyntaxError that reads to the user like a bug in our client.
      const body = await response.json().catch(() => ({}));
      const error = body as ApiError;
      throw new ApiRequestError(
        error.detail || "Request failed",
        body,
        response.status,
      );
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }
}
