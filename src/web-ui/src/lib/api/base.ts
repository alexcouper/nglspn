import type { components } from "../api-types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ApiError = components["schemas"]["Error"];

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public body: Record<string, unknown>,
    public status: number = 0,
  ) {
    super(message);
  }
}

type RefreshOutcome = "refreshed" | "invalid" | "transient";

export class APIClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<RefreshOutcome> | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      this.refreshToken = localStorage.getItem("refresh_token");
    }
  }

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);
      document.cookie = "logged_in=true; path=/; SameSite=Lax";
    }
  }

  private setAccessToken(access: string) {
    this.accessToken = access;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      document.cookie = "logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
    }
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  private async attemptTokenRefresh(): Promise<RefreshOutcome> {
    if (!this.refreshToken) {
      return "invalid";
    }

    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = (async (): Promise<RefreshOutcome> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (response.status === 401) {
          return "invalid";
        }

        if (!response.ok) {
          return "transient";
        }

        const data = await response.json();
        this.setAccessToken(data.access_token);
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
        throw new Error("Unauthorized");
      }

      // transient: refresh request failed for non-credential reasons
      // (network blip, 5xx, rate limit). Keep tokens so the user stays
      // logged in once connectivity / the backend recovers.
      throw new Error("Token refresh failed");
    }

    if (response.status === 401) {
      this.clearTokens();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("auth:logout"));
      }
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const body = await response.json();
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
