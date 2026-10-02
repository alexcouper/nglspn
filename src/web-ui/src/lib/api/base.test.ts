import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  APIClient,
  ApiRequestError,
  AuthExpiredError,
  AuthTransientError,
} from "./base";
import { seedAccessToken, seedLegacyRefreshToken } from "@/test/factories";
import {
  expectLoggedOut,
  expectNoStoredRefreshToken,
  expectStillLoggedIn,
  jsonResponse,
  mockFetchSequence,
  networkError,
  requestsTo,
  type FetchMock,
} from "@/test/helpers";

const newAccess = "fresh-access-token";

const accessExpired = () => jsonResponse({ status: 401 });
const refreshSucceeds = () =>
  jsonResponse({ body: { access_token: newAccess, token_type: "bearer" } });
const refreshRejected = () =>
  jsonResponse({ status: 401, body: { detail: "Invalid or expired refresh token" } });
const refreshUnavailable = () =>
  jsonResponse({ status: 503, body: { detail: "Service Unavailable" } });

function refreshRequests(fetchMock: FetchMock) {
  return requestsTo(fetchMock, "/api/auth/refresh");
}

function listenFor(eventName: string) {
  const listener = vi.fn();
  window.addEventListener(eventName, listener);
  return listener;
}

describe("APIClient", () => {
  let accessToken: string;
  let client: APIClient;

  beforeEach(() => {
    accessToken = seedAccessToken();
    client = new APIClient();
  });

  describe("on a successful authenticated request", () => {
    it("sends the access token as a Bearer header", async () => {
      const fetchMock = mockFetchSequence(jsonResponse({ body: { ok: true } }));

      await client.request("/api/anything");

      const [{ init }] = requestsTo(fetchMock);
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe(`Bearer ${accessToken}`);
    });

    it("returns the parsed JSON body", async () => {
      mockFetchSequence(jsonResponse({ body: { hello: "world" } }));

      const result = await client.request<{ hello: string }>("/api/anything");

      expect(result.hello).toBe("world");
    });

    it("does not send cookies to endpoints that never read them", async () => {
      const fetchMock = mockFetchSequence(jsonResponse({ body: { ok: true } }));

      await client.request("/api/anything");

      const [{ init }] = requestsTo(fetchMock);
      expect(init.credentials).toBeUndefined();
    });
  });

  describe("when the access token has expired", () => {
    it("refreshes the access token and retries the original request", async () => {
      const fetchMock = mockFetchSequence(
        accessExpired(),
        refreshSucceeds(),
        jsonResponse({ body: { hello: "world" } }),
      );

      const result = await client.request<{ hello: string }>("/api/anything");

      expect(result.hello).toBe("world");
      expect(fetchMock).toHaveBeenCalledTimes(3);
      const retryHeaders = requestsTo(fetchMock)[2].init.headers as Record<string, string>;
      expect(retryHeaders["Authorization"]).toBe(`Bearer ${newAccess}`);
    });

    it("lets the browser attach the refresh cookie and sends no body", async () => {
      const fetchMock = mockFetchSequence(
        accessExpired(),
        refreshSucceeds(),
        jsonResponse({ body: {} }),
      );

      await client.request("/api/anything");

      const [{ init }] = refreshRequests(fetchMock);
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
      expect(init.body).toBeUndefined();
    });

    it("persists the new access token to localStorage", async () => {
      mockFetchSequence(accessExpired(), refreshSucceeds(), jsonResponse({ body: {} }));

      await client.request("/api/anything");

      expect(localStorage.getItem("access_token")).toBe(newAccess);
    });

    it("never stores a refresh token", async () => {
      mockFetchSequence(accessExpired(), refreshSucceeds(), jsonResponse({ body: {} }));

      await client.request("/api/anything");

      expectNoStoredRefreshToken();
    });

    it("announces the successful refresh", async () => {
      const refreshed = listenFor("auth:refreshed");
      mockFetchSequence(accessExpired(), refreshSucceeds(), jsonResponse({ body: {} }));

      await client.request("/api/anything");

      expect(refreshed).toHaveBeenCalledTimes(1);
    });

    it("only attempts to refresh once per request", async () => {
      const fetchMock = mockFetchSequence(
        accessExpired(),
        refreshSucceeds(),
        accessExpired(),
      );

      await expect(client.request("/api/anything")).rejects.toThrow("Unauthorized");
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("shares one refresh between requests that expire together", async () => {
      const fetchMock = mockFetchSequence(
        accessExpired(),
        accessExpired(),
        refreshSucceeds(),
        jsonResponse({ body: {} }),
        jsonResponse({ body: {} }),
      );

      await Promise.all([client.request("/api/one"), client.request("/api/two")]);

      expect(refreshRequests(fetchMock)).toHaveLength(1);
    });
  });

  describe("when the refresh token is genuinely invalid", () => {
    it("clears tokens after a 401 from the refresh endpoint", async () => {
      mockFetchSequence(accessExpired(), refreshRejected());

      await expect(client.request("/api/anything")).rejects.toThrow("Unauthorized");
      expectLoggedOut();
    });

    it("throws AuthExpiredError so callers can say the session ended", async () => {
      mockFetchSequence(accessExpired(), refreshRejected());

      const err = await client.request("/api/anything").catch((e) => e);

      expect(err).toBeInstanceOf(AuthExpiredError);
      expect(err).not.toBeInstanceOf(AuthTransientError);
    });

    it("does not announce a refresh", async () => {
      const refreshed = listenFor("auth:refreshed");
      mockFetchSequence(accessExpired(), refreshRejected());

      await client.request("/api/anything").catch(() => {});

      expect(refreshed).not.toHaveBeenCalled();
    });
  });

  describe("when the refresh request fails for non-credential reasons", () => {
    // The distinction callers show to a person is carried by the error's type,
    // not by its message. If these two ever became the same class, everything
    // downstream would start telling people they had been logged out when they
    // had not.
    it("throws AuthTransientError, not AuthExpiredError", async () => {
      mockFetchSequence(accessExpired(), refreshUnavailable());

      const err = await client.request("/api/anything").catch((e) => e);

      expect(err).toBeInstanceOf(AuthTransientError);
      expect(err).not.toBeInstanceOf(AuthExpiredError);
      expectStillLoggedIn(accessToken);
    });

    it("does not clear tokens when fetch throws a network error", async () => {
      mockFetchSequence(accessExpired(), networkError("offline"));

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(accessToken);
    });

    it("does not clear tokens when the refresh endpoint returns 503", async () => {
      mockFetchSequence(accessExpired(), refreshUnavailable());

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(accessToken);
    });

    it("does not clear tokens when the refresh endpoint returns 500", async () => {
      mockFetchSequence(
        accessExpired(),
        jsonResponse({ status: 500, body: { detail: "Internal Server Error" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(accessToken);
    });

    it("does not clear tokens when the refresh endpoint is rate-limited (429)", async () => {
      mockFetchSequence(
        accessExpired(),
        jsonResponse({ status: 429, body: { detail: "Too Many Requests" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(accessToken);
    });
  });

  describe("when an error response is not JSON", () => {
    it("reports the status rather than a JSON parse failure", async () => {
      // A 502 from the proxy is an HTML page. An unguarded json() here used to
      // surface `Unexpected token '<'` to the user, which reads like a bug in
      // our client.
      mockFetchSequence(
        new Response("<html><body>502 Bad Gateway</body></html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      );

      const err = await client.request("/api/anything").catch((e) => e);

      expect(err).toBeInstanceOf(ApiRequestError);
      expect((err as ApiRequestError).status).toBe(502);
      expect((err as ApiRequestError).message).not.toContain("JSON");
    });
  });

  describe("when no refresh token is held locally", () => {
    // The refresh token is an HttpOnly cookie now: script cannot see whether
    // one exists, so the only way to find out is to ask.
    it("still calls the refresh endpoint", async () => {
      const fetchMock = mockFetchSequence(
        accessExpired(),
        refreshSucceeds(),
        jsonResponse({ body: { hello: "world" } }),
      );

      const result = await client.request<{ hello: string }>("/api/anything");

      expect(refreshRequests(fetchMock)).toHaveLength(1);
      expect(result.hello).toBe("world");
    });

    it("clears tokens when the backend says there is no session", async () => {
      mockFetchSequence(accessExpired(), refreshRejected());

      await expect(client.request("/api/anything")).rejects.toThrow("Unauthorized");

      expectLoggedOut();
    });
  });

  describe("refreshSession", () => {
    it("resolves and stores the access token when the cookie is accepted", async () => {
      mockFetchSequence(refreshSucceeds());

      await client.refreshSession();

      expect(localStorage.getItem("access_token")).toBe(newAccess);
      expect(client.isAuthenticated()).toBe(true);
    });

    it("throws AuthExpiredError when there is no session to refresh", async () => {
      mockFetchSequence(refreshRejected());

      await expect(client.refreshSession()).rejects.toBeInstanceOf(AuthExpiredError);
    });

    it("throws AuthTransientError when the backend cannot be reached", async () => {
      mockFetchSequence(networkError("offline"));

      await expect(client.refreshSession()).rejects.toBeInstanceOf(AuthTransientError);
    });
  });

  describe("setSession", () => {
    it("stores only the access token", () => {
      client.setSession(newAccess);

      expect(localStorage.getItem("access_token")).toBe(newAccess);
      expectNoStoredRefreshToken();
    });

  });

  describe("on construction", () => {
    it("removes a refresh token left in localStorage by an older build", () => {
      seedLegacyRefreshToken();

      new APIClient();

      expectNoStoredRefreshToken();
    });
  });
});
