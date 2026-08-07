import { beforeEach, describe, expect, it } from "vitest";
import {
  APIClient,
  ApiRequestError,
  AuthExpiredError,
  AuthTransientError,
} from "./base";
import { makeTokenPair, seedTokens, type TokenPair } from "@/test/factories";
import {
  expectLoggedOut,
  expectStillLoggedIn,
  jsonResponse,
  mockFetchSequence,
  networkError,
} from "@/test/helpers";

describe("APIClient", () => {
  let tokens: TokenPair;
  let client: APIClient;

  beforeEach(() => {
    tokens = makeTokenPair();
    seedTokens(tokens);
    client = new APIClient();
  });

  describe("on a successful authenticated request", () => {
    it("sends the access token as a Bearer header", async () => {
      const fetchMock = mockFetchSequence(jsonResponse({ body: { ok: true } }));

      await client.request("/api/anything");

      const init = fetchMock.mock.calls[0][1] as RequestInit;
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe(`Bearer ${tokens.access}`);
    });

    it("returns the parsed JSON body", async () => {
      mockFetchSequence(jsonResponse({ body: { hello: "world" } }));

      const result = await client.request<{ hello: string }>("/api/anything");

      expect(result.hello).toBe("world");
    });
  });

  describe("when the access token has expired", () => {
    const newAccess = "fresh-access-token";

    it("refreshes the access token and retries the original request", async () => {
      const fetchMock = mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ body: { access_token: newAccess, token_type: "bearer" } }),
        jsonResponse({ body: { hello: "world" } }),
      );

      const result = await client.request<{ hello: string }>("/api/anything");

      expect(result.hello).toBe("world");
      expect(fetchMock).toHaveBeenCalledTimes(3);
      const retryInit = fetchMock.mock.calls[2][1] as RequestInit;
      const retryHeaders = retryInit.headers as Record<string, string>;
      expect(retryHeaders["Authorization"]).toBe(`Bearer ${newAccess}`);
    });

    it("persists the new access token to localStorage", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ body: { access_token: newAccess } }),
        jsonResponse({ body: {} }),
      );

      await client.request("/api/anything");

      expect(localStorage.getItem("access_token")).toBe(newAccess);
      expect(localStorage.getItem("refresh_token")).toBe(tokens.refresh);
    });

    it("only attempts to refresh once per request", async () => {
      const fetchMock = mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ body: { access_token: newAccess } }),
        jsonResponse({ status: 401 }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow("Unauthorized");
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });
  });

  describe("when the refresh token is genuinely invalid", () => {
    it("clears tokens after a 401 from the refresh endpoint", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 401, body: { detail: "Invalid or expired refresh token" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow("Unauthorized");
      expectLoggedOut();
    });

    it("throws AuthExpiredError so callers can say the session ended", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 401, body: { detail: "Invalid or expired refresh token" } }),
      );

      const err = await client.request("/api/anything").catch((e) => e);

      expect(err).toBeInstanceOf(AuthExpiredError);
      expect(err).not.toBeInstanceOf(AuthTransientError);
    });
  });

  describe("when the refresh request fails for non-credential reasons", () => {
    // The distinction callers show to a person is carried by the error's type,
    // not by its message. If these two ever became the same class, everything
    // downstream would start telling people they had been logged out when they
    // had not.
    it("throws AuthTransientError, not AuthExpiredError", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 503, body: { detail: "Service Unavailable" } }),
      );

      const err = await client.request("/api/anything").catch((e) => e);

      expect(err).toBeInstanceOf(AuthTransientError);
      expect(err).not.toBeInstanceOf(AuthExpiredError);
      expectStillLoggedIn(tokens);
    });

    it("does not clear tokens when fetch throws a network error", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        networkError("offline"),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(tokens);
    });

    it("does not clear tokens when the refresh endpoint returns 503", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 503, body: { detail: "Service Unavailable" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(tokens);
    });

    it("does not clear tokens when the refresh endpoint returns 500", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 500, body: { detail: "Internal Server Error" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(tokens);
    });

    it("does not clear tokens when the refresh endpoint is rate-limited (429)", async () => {
      mockFetchSequence(
        jsonResponse({ status: 401 }),
        jsonResponse({ status: 429, body: { detail: "Too Many Requests" } }),
      );

      await expect(client.request("/api/anything")).rejects.toThrow();

      expectStillLoggedIn(tokens);
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

  describe("when there is no refresh token at all", () => {
    it("clears tokens and rejects without calling the refresh endpoint", async () => {
      localStorage.removeItem("refresh_token");
      const clientWithoutRefresh = new APIClient();
      const fetchMock = mockFetchSequence(jsonResponse({ status: 401 }));

      await expect(clientWithoutRefresh.request("/api/anything")).rejects.toThrow("Unauthorized");

      expect(fetchMock).toHaveBeenCalledTimes(1);
      expectLoggedOut();
    });
  });
});
