import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { makeUser, seedAccessToken } from "@/test/factories";
import {
  jsonResponse,
  mockFetchSequence,
  type FetchStep,
} from "@/test/helpers";

const PROTECTED_PATH = "/my-projects";

const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => PROTECTED_PATH,
}));

const unmountAll: Array<() => Promise<void>> = [];

// A page behind useRequireAuth, under the real AuthProvider. Modules are
// re-imported per mount so the `api` singleton reads localStorage as seeded.
async function mountProtectedPage() {
  vi.resetModules();
  const [{ AuthProvider }, { useRequireAuth }, React] = await Promise.all([
    import("@/contexts/auth"),
    import("./useRequireAuth"),
    import("react"),
  ]);

  function ProtectedPage() {
    useRequireAuth();
    return null;
  }

  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  unmountAll.push(() => act(async () => root.unmount()));

  await act(async () => {
    root.render(
      React.createElement(AuthProvider, null, React.createElement(ProtectedPage)),
    );
  });
}

const me = () => jsonResponse({ body: makeUser() });
const unavailable = () =>
  jsonResponse({ status: 503, body: { detail: "Service Unavailable" } });
const accessExpired = () => jsonResponse({ status: 401 });
const refreshRejected = () =>
  jsonResponse({ status: 401, body: { detail: "Invalid or expired refresh token" } });

/** Queues a response for the first attempt and for each of the three retries. */
function everyStartupAttempt(step: () => FetchStep): FetchStep[] {
  return [step(), step(), step(), step()];
}

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function expectNoRedirect() {
  expect(router.push).not.toHaveBeenCalled();
}

function expectRedirectToLoginWithReturnPath() {
  expect(router.push).toHaveBeenCalledWith(
    `/login?next=${encodeURIComponent(PROTECTED_PATH)}`,
  );
}

describe("useRequireAuth", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    router.push.mockClear();
  });

  afterEach(async () => {
    for (const unmount of unmountAll.splice(0)) {
      await unmount();
    }
    vi.useRealTimers();
  });

  describe("with an access token held", () => {
    beforeEach(() => {
      seedAccessToken();
    });

    it("does not redirect a signed-in user", async () => {
      mockFetchSequence(me());

      await mountProtectedPage();

      expectNoRedirect();
    });

    it("does not redirect while the startup check is retrying", async () => {
      mockFetchSequence(...everyStartupAttempt(unavailable));

      await mountProtectedPage();
      expectNoRedirect();
      await advance(1000);
      expectNoRedirect();
      await advance(3000);
      expectNoRedirect();
    });

    it("does not redirect after the retries run out, while the token is still held", async () => {
      mockFetchSequence(...everyStartupAttempt(unavailable));

      await mountProtectedPage();
      await advance(1000 + 3000 + 8000);

      expectNoRedirect();
    });

    it("stays on the page when a retry succeeds", async () => {
      mockFetchSequence(unavailable(), me());

      await mountProtectedPage();
      await advance(1000);

      expectNoRedirect();
    });

    it("redirects to login with a return path once the refresh token is rejected", async () => {
      mockFetchSequence(accessExpired(), refreshRejected());

      await mountProtectedPage();

      expectRedirectToLoginWithReturnPath();
    });
  });

  describe("with no access token", () => {
    it("redirects to login with a return path when there is no session to restore", async () => {
      mockFetchSequence(refreshRejected());

      await mountProtectedPage();

      expectRedirectToLoginWithReturnPath();
    });
  });
});
