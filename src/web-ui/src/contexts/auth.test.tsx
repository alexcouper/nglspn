import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { User } from "@/lib/api";
import { makeUser, seedAccessToken } from "@/test/factories";
import {
  expectLoggedOut,
  expectStillLoggedIn,
  jsonResponse,
  mockFetchSequence,
  networkError,
  requestsTo,
  type FetchStep,
} from "@/test/helpers";

interface AuthSnapshot {
  isLoading: boolean;
  user: User | null;
}

// A provider left mounted keeps listening on window and would answer the next
// test's events with requests of its own.
const unmountAll: Array<() => Promise<void>> = [];

// The module is re-imported per mount so the `api` singleton reads localStorage
// as the test seeded it, the way a page load would.
async function mountAuthProvider() {
  vi.resetModules();
  const [{ AuthProvider, useAuth }, React] = await Promise.all([
    import("./auth"),
    import("react"),
  ]);

  // Everything the provider has shown, in order, plus its current value.
  const renders: AuthSnapshot[] = [];
  let latest!: ReturnType<typeof useAuth>;
  function Probe() {
    const auth = useAuth();
    React.useEffect(() => {
      latest = auth;
      renders.push({ isLoading: auth.isLoading, user: auth.user });
    });
    return null;
  }

  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  await act(async () => {
    root.render(
      React.createElement(AuthProvider, null, React.createElement(Probe)),
    );
  });

  const unmount = () => act(async () => root.unmount());
  unmountAll.push(unmount);

  return { auth: () => latest, renders, unmount };
}

type MountedAuth = Awaited<ReturnType<typeof mountAuthProvider>>;

const me = (user: User) => jsonResponse({ body: user });
const unavailable = () =>
  jsonResponse({ status: 503, body: { detail: "Service Unavailable" } });
const accessExpired = () => jsonResponse({ status: 401 });
const refreshRejected = () =>
  jsonResponse({ status: 401, body: { detail: "Invalid or expired refresh token" } });
const refreshSucceeds = () =>
  jsonResponse({ body: { access_token: "fresh-access-token", token_type: "bearer" } });
const logoutSucceeds = () => new Response(null, { status: 204 });
// Rejects only when fetch reaches this step. A promise rejected up front would
// sit unhandled while earlier steps and retry timers run.
const offline = (): FetchStep => () => networkError();

/** Queues a response for the first attempt and for each of the three retries. */
function everyStartupAttempt(step: () => FetchStep): FetchStep[] {
  return [step(), step(), step(), step()];
}

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function exhaustStartupRetries() {
  await advance(1000 + 3000 + 8000);
}

async function dispatch(target: EventTarget, eventName: string) {
  await act(async () => {
    target.dispatchEvent(new Event(eventName));
  });
}

function setTabVisibility(state: DocumentVisibilityState) {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue(state);
}

function expectLoading({ auth }: MountedAuth) {
  expect(auth().isLoading).toBe(true);
  expect(auth().user).toBeNull();
}

function expectSignedInAs({ auth }: MountedAuth, user: User) {
  expect(auth().isLoading).toBe(false);
  expect(auth().user).toEqual(user);
}

function expectShownAsLoggedOut({ auth }: MountedAuth) {
  expect(auth().isLoading).toBe(false);
  expect(auth().user).toBeNull();
}

function expectNeverShownAsLoggedOut({ renders }: MountedAuth) {
  const loggedOutRenders = renders.filter((r) => !r.isLoading && r.user === null);
  expect(loggedOutRenders).toEqual([]);
}

describe("AuthProvider", () => {
  let user: User;

  beforeEach(() => {
    vi.useFakeTimers();
    user = makeUser();
  });

  afterEach(async () => {
    for (const unmount of unmountAll.splice(0)) {
      await unmount();
    }
    vi.useRealTimers();
  });

  describe("on mount with an access token", () => {
    let accessToken: string;

    beforeEach(() => {
      accessToken = seedAccessToken();
    });

    it("shows the user when the check succeeds", async () => {
      mockFetchSequence(me(user));

      const mounted = await mountAuthProvider();

      expectSignedInAs(mounted, user);
    });

    it("keeps tokens when /me triggers a transient (5xx) refresh failure", async () => {
      mockFetchSequence(accessExpired(), unavailable());

      await mountAuthProvider();

      expectStillLoggedIn(accessToken);
    });

    it("shows the user after a 503 then a 200, never as logged out in between", async () => {
      mockFetchSequence(unavailable(), me(user));

      const mounted = await mountAuthProvider();
      expectLoading(mounted);
      await advance(1000);

      expectSignedInAs(mounted, user);
      expectNeverShownAsLoggedOut(mounted);
      expectStillLoggedIn(accessToken);
    });

    it("retries after 1 s, 3 s and 8 s", async () => {
      const fetchMock = mockFetchSequence(...everyStartupAttempt(unavailable));

      await mountAuthProvider();
      expect(fetchMock).toHaveBeenCalledTimes(1);

      await advance(999);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      await advance(1);
      expect(fetchMock).toHaveBeenCalledTimes(2);

      await advance(2999);
      expect(fetchMock).toHaveBeenCalledTimes(2);
      await advance(1);
      expect(fetchMock).toHaveBeenCalledTimes(3);

      await advance(7999);
      expect(fetchMock).toHaveBeenCalledTimes(3);
      await advance(1);
      expect(fetchMock).toHaveBeenCalledTimes(4);
    });

    it("stays in the loading state for as long as it is retrying", async () => {
      mockFetchSequence(...everyStartupAttempt(unavailable));

      const mounted = await mountAuthProvider();
      await advance(1000 + 3000 + 7999);

      expectLoading(mounted);
    });

    it("recovers on a later retry when the network comes back", async () => {
      mockFetchSequence(offline(), offline(), me(user));

      const mounted = await mountAuthProvider();
      await advance(1000 + 3000);

      expectSignedInAs(mounted, user);
      expectNeverShownAsLoggedOut(mounted);
    });

    describe("when every startup attempt fails", () => {
      it("keeps the token and stops showing the placeholder", async () => {
        const fetchMock = mockFetchSequence(...everyStartupAttempt(unavailable));

        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        expectShownAsLoggedOut(mounted);
        expectStillLoggedIn(accessToken);
        expect(fetchMock).toHaveBeenCalledTimes(4);
      });

      it("keeps the token when the failures were network errors", async () => {
        mockFetchSequence(...everyStartupAttempt(offline));

        await mountAuthProvider();
        await exhaustStartupRetries();

        expectStillLoggedIn(accessToken);
      });

      it("does not keep polling on a timer", async () => {
        const fetchMock = mockFetchSequence(...everyStartupAttempt(unavailable));

        await mountAuthProvider();
        await exhaustStartupRetries();
        await advance(60_000);

        expect(fetchMock).toHaveBeenCalledTimes(4);
      });

      it("recovers when the browser comes back online", async () => {
        mockFetchSequence(...everyStartupAttempt(offline), me(user));
        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        await dispatch(window, "online");

        expectSignedInAs(mounted, user);
      });

      it("recovers when the tab becomes visible again", async () => {
        mockFetchSequence(...everyStartupAttempt(unavailable), me(user));
        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        setTabVisibility("visible");
        await dispatch(document, "visibilitychange");

        expectSignedInAs(mounted, user);
      });

      it("does not check again when the tab is hidden", async () => {
        const fetchMock = mockFetchSequence(...everyStartupAttempt(unavailable));
        await mountAuthProvider();
        await exhaustStartupRetries();

        setTabVisibility("hidden");
        await dispatch(document, "visibilitychange");

        expect(fetchMock).toHaveBeenCalledTimes(4);
      });

      it("recovers when a later request refreshes the session", async () => {
        mockFetchSequence(...everyStartupAttempt(unavailable), me(user));
        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        await dispatch(window, "auth:refreshed");

        expectSignedInAs(mounted, user);
      });

      it("keeps listening when a recovery attempt fails too", async () => {
        mockFetchSequence(
          ...everyStartupAttempt(unavailable),
          unavailable(),
          me(user),
        );
        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        await dispatch(window, "online");
        expectShownAsLoggedOut(mounted);
        await dispatch(window, "online");

        expectSignedInAs(mounted, user);
      });

      it("stops listening once unmounted", async () => {
        const fetchMock = mockFetchSequence(...everyStartupAttempt(unavailable));
        const mounted = await mountAuthProvider();
        await exhaustStartupRetries();

        await mounted.unmount();
        await dispatch(window, "online");
        await dispatch(window, "auth:refreshed");

        expect(fetchMock).toHaveBeenCalledTimes(4);
      });
    });

    it("stops retrying once unmounted", async () => {
      const fetchMock = mockFetchSequence(unavailable());
      const mounted = await mountAuthProvider();

      await mounted.unmount();
      await advance(1000 + 3000 + 8000);

      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("does not re-check on events once the user is known", async () => {
      const fetchMock = mockFetchSequence(me(user));
      await mountAuthProvider();

      await dispatch(window, "online");
      await dispatch(window, "auth:refreshed");

      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    describe("when the refresh token is rejected", () => {
      it("clears the token and shows logged out at once, without retrying", async () => {
        const fetchMock = mockFetchSequence(accessExpired(), refreshRejected());

        const mounted = await mountAuthProvider();

        expectShownAsLoggedOut(mounted);
        expectLoggedOut();

        await advance(1000 + 3000 + 8000);
        expect(fetchMock).toHaveBeenCalledTimes(2);
      });

      it("does not re-check when the browser comes back online", async () => {
        const fetchMock = mockFetchSequence(accessExpired(), refreshRejected());
        await mountAuthProvider();

        await dispatch(window, "online");

        expect(fetchMock).toHaveBeenCalledTimes(2);
      });
    });
  });

  // The refresh cookie outlives localStorage (Safari purges the latter after a
  // week without a visit), so an empty localStorage is not proof of no session.
  describe("on mount without an access token", () => {
    it("restores the session from the refresh cookie", async () => {
      const fetchMock = mockFetchSequence(refreshSucceeds(), me(user));

      const mounted = await mountAuthProvider();

      expectSignedInAs(mounted, user);
      expectNeverShownAsLoggedOut(mounted);
      expect(requestsTo(fetchMock, "/api/auth/refresh")).toHaveLength(1);
    });

    it("shows logged out after a single request when there is no session", async () => {
      const fetchMock = mockFetchSequence(refreshRejected());

      const mounted = await mountAuthProvider();

      expectShownAsLoggedOut(mounted);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("logout", () => {
    let mounted: MountedAuth;

    beforeEach(async () => {
      seedAccessToken();
      mockFetchSequence(me(user));
      mounted = await mountAuthProvider();
    });

    it("expires the refresh cookie through the backend and clears the access token", async () => {
      const fetchMock = mockFetchSequence(logoutSucceeds());

      await act(() => mounted.auth().logout());

      expect(requestsTo(fetchMock, "/api/auth/logout")).toHaveLength(1);
      expectShownAsLoggedOut(mounted);
      expectLoggedOut();
    });

    it("clears the access token and shows logged out when the request fails", async () => {
      mockFetchSequence(offline());

      await act(() => mounted.auth().logout());

      expectShownAsLoggedOut(mounted);
      expectLoggedOut();
    });

    it("shows logged out before the backend has answered", async () => {
      let answer!: (response: Response) => void;
      mockFetchSequence(new Promise<Response>((resolve) => (answer = resolve)));

      let loggingOut!: Promise<void>;
      await act(async () => {
        loggingOut = mounted.auth().logout();
      });

      expectShownAsLoggedOut(mounted);
      expectLoggedOut();

      answer(logoutSucceeds());
      await act(() => loggingOut);
    });
  });
});
