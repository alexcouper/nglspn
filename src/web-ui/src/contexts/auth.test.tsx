import { describe, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { makeTokenPair, seedTokens } from "@/test/factories";
import {
  expectStillLoggedIn,
  jsonResponse,
  mockFetchSequence,
} from "@/test/helpers";

async function mountAuthProvider() {
  vi.resetModules();
  const [{ AuthProvider }, React] = await Promise.all([
    import("./auth"),
    import("react"),
  ]);
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  await act(async () => {
    root.render(
      React.createElement(AuthProvider, null, React.createElement("div")),
    );
  });

  return { root, container };
}

describe("AuthProvider on initial mount", () => {
  it("keeps tokens when /me triggers a transient (5xx) refresh failure", async () => {
    const tokens = makeTokenPair();
    seedTokens(tokens);
    mockFetchSequence(
      jsonResponse({ status: 401 }),
      jsonResponse({ status: 503, body: { detail: "Service Unavailable" } }),
    );

    await mountAuthProvider();

    expectStillLoggedIn(tokens);
  });
});
