import { beforeEach, describe, expect, it } from "vitest";
import { AuthClient } from "./auth";
import { APIClient, AuthExpiredError, AuthTransientError } from "./base";
import { seedLegacyRefreshToken } from "@/test/factories";
import {
  expectLoggedOut,
  expectNoStoredRefreshToken,
  jsonResponse,
  mockFetchSequence,
  networkError,
  requestsTo,
} from "@/test/helpers";

const loginSucceeds = (accessToken = "access-from-login") =>
  jsonResponse({
    body: { access_token: accessToken, token_type: "bearer", is_verified: true },
  });
const logoutSucceeds = () => new Response(null, { status: 204 });
const refreshSucceeds = (accessToken = "access-from-refresh") =>
  jsonResponse({ body: { access_token: accessToken, token_type: "bearer" } });
const noSession = () => jsonResponse({ status: 401, body: { detail: "No session" } });

function makeAuthClient() {
  const client = new APIClient();
  return { client, auth: new AuthClient(client) };
}

async function logOutWhileBackendIsUnreachable() {
  const { auth } = makeAuthClient();
  mockFetchSequence(networkError("offline"));
  await auth.logout().catch(() => {});
}

describe("AuthClient", () => {
  describe("login", () => {
    it("stores only the access token", async () => {
      const { auth } = makeAuthClient();
      mockFetchSequence(loginSucceeds("access-from-login"));

      await auth.login("user@example.com", "password");

      expect(localStorage.getItem("access_token")).toBe("access-from-login");
      expectNoStoredRefreshToken();
    });

    it("lets the browser keep the refresh cookie the response sets", async () => {
      const { auth } = makeAuthClient();
      const fetchMock = mockFetchSequence(loginSucceeds());

      await auth.login("user@example.com", "password");

      const [{ init }] = requestsTo(fetchMock, "/api/auth/login");
      expect(init.credentials).toBe("include");
    });

    it("discards a refresh token left in localStorage by an older version", async () => {
      seedLegacyRefreshToken();
      const { auth } = makeAuthClient();
      mockFetchSequence(loginSucceeds());

      await auth.login("user@example.com", "password");

      expectNoStoredRefreshToken();
    });
  });

  describe("logout", () => {
    it("asks the backend to expire the refresh cookie", async () => {
      const { auth } = makeAuthClient();
      const fetchMock = mockFetchSequence(logoutSucceeds());

      await auth.logout();

      const [{ init }] = requestsTo(fetchMock, "/api/auth/logout");
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
    });

    it("rejects when the backend cannot be reached", async () => {
      const { auth } = makeAuthClient();
      mockFetchSequence(networkError("offline"));

      await expect(auth.logout()).rejects.toThrow();
    });
  });

  describe("restoreSession", () => {
    it("obtains an access token from the refresh cookie", async () => {
      const { client, auth } = makeAuthClient();
      const fetchMock = mockFetchSequence(refreshSucceeds("access-from-refresh"));

      await auth.restoreSession();

      expect(client.isAuthenticated()).toBe(true);
      expect(localStorage.getItem("access_token")).toBe("access-from-refresh");
      expect(requestsTo(fetchMock, "/api/auth/refresh")).toHaveLength(1);
    });

    it("throws AuthExpiredError when there is no session", async () => {
      const { auth } = makeAuthClient();
      mockFetchSequence(noSession());

      await expect(auth.restoreSession()).rejects.toBeInstanceOf(AuthExpiredError);
      expectLoggedOut();
    });

    it("throws AuthTransientError when the backend cannot be asked", async () => {
      const { auth } = makeAuthClient();
      mockFetchSequence(networkError("offline"));

      await expect(auth.restoreSession()).rejects.toBeInstanceOf(AuthTransientError);
    });
  });

  // A logout that never reached the backend leaves the HttpOnly cookie in the
  // browser. Restoring from it would undo the logout.
  describe("after a logout that did not reach the backend", () => {
    beforeEach(logOutWhileBackendIsUnreachable);

    it("finishes the logout instead of restoring the session", async () => {
      const { auth } = makeAuthClient();
      const fetchMock = mockFetchSequence(logoutSucceeds());

      await expect(auth.restoreSession()).rejects.toBeInstanceOf(AuthExpiredError);

      expect(requestsTo(fetchMock, "/api/auth/logout")).toHaveLength(1);
      expect(requestsTo(fetchMock, "/api/auth/refresh")).toHaveLength(0);
      expectLoggedOut();
    });

    it("does not restore the session while the backend is still unreachable", async () => {
      const { auth } = makeAuthClient();
      const fetchMock = mockFetchSequence(networkError("offline"));

      await expect(auth.restoreSession()).rejects.toBeInstanceOf(AuthExpiredError);

      expect(requestsTo(fetchMock, "/api/auth/refresh")).toHaveLength(0);
      expectLoggedOut();
    });

    it("keeps trying on later page loads until the logout goes through", async () => {
      const { auth } = makeAuthClient();
      mockFetchSequence(networkError("offline"));
      await auth.restoreSession().catch(() => {});

      const fetchMock = mockFetchSequence(logoutSucceeds());
      await auth.restoreSession().catch(() => {});

      expect(requestsTo(fetchMock, "/api/auth/logout")).toHaveLength(1);
    });

    it("restores normally once the logout has gone through", async () => {
      const { client, auth } = makeAuthClient();
      mockFetchSequence(logoutSucceeds());
      await auth.restoreSession().catch(() => {});

      mockFetchSequence(refreshSucceeds());
      await auth.restoreSession();

      expect(client.isAuthenticated()).toBe(true);
    });

    it("is forgotten by a new login", async () => {
      const { client, auth } = makeAuthClient();
      mockFetchSequence(loginSucceeds());
      await auth.login("user@example.com", "password");
      client.clearTokens();

      const fetchMock = mockFetchSequence(refreshSucceeds());
      await auth.restoreSession();

      expect(requestsTo(fetchMock, "/api/auth/logout")).toHaveLength(0);
      expect(client.isAuthenticated()).toBe(true);
    });
  });
});
