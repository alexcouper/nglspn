import { expect, vi } from "vitest";

export type FetchMock = ReturnType<typeof vi.fn>;

export interface JsonResponseInit {
  status?: number;
  body?: unknown;
}

export function jsonResponse({ status = 200, body = {} }: JsonResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function networkError(message = "network down"): Promise<never> {
  return Promise.reject(new TypeError(message));
}

export type FetchStep = Response | Promise<Response> | Error | (() => Response | Promise<Response>);

export function mockFetchSequence(...steps: FetchStep[]): FetchMock {
  let i = 0;
  const fetchMock = vi.fn(async () => {
    if (i >= steps.length) {
      throw new Error(`fetch called ${i + 1} times but only ${steps.length} responses queued`);
    }
    const step = steps[i++];
    if (step instanceof Error) throw step;
    if (typeof step === "function") return step();
    return step;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function expectStillLoggedIn(tokens: { access: string; refresh: string }) {
  expect(localStorage.getItem("access_token")).toBe(tokens.access);
  expect(localStorage.getItem("refresh_token")).toBe(tokens.refresh);
}

export function expectLoggedOut() {
  expect(localStorage.getItem("access_token")).toBeNull();
  expect(localStorage.getItem("refresh_token")).toBeNull();
}
