import { describe, expect, it } from "vitest";
import { ApiRequestError, AuthExpiredError, AuthTransientError } from "./base";
import { describeApiError } from "./errors";

const FALLBACK = "Couldn't save this article.";

// --------------------------------------------------------------- factories

function apiError(status: number, detail?: unknown): ApiRequestError {
  const body = detail === undefined ? {} : { detail };
  return new ApiRequestError(
    typeof detail === "string" ? detail : "Request failed",
    body,
    status,
  );
}

function messageFor(err: unknown): string {
  return describeApiError(err, FALLBACK);
}

// ----------------------------------------------------------------- asserts

function expectSaysWorkIsSafe(message: string) {
  expect(message).toContain("your work is still here");
  expect(message).not.toContain("sign in");
  expect(message).not.toContain("Sign in");
}

function expectSaysSessionEnded(message: string) {
  expect(message).toBe("Your session has ended. Sign in again to continue.");
}

// ------------------------------------------------------------------- tests

describe("describeApiError", () => {
  it("tells the user to retry when the token refresh failed transiently", () => {
    expect(messageFor(new AuthTransientError())).toBe(
      "Couldn't reach the server. Nothing was sent — your work is still here. Try again.",
    );
  });

  it("does not claim the session ended when the tokens were kept", () => {
    expectSaysWorkIsSafe(messageFor(new AuthTransientError()));
  });

  it("says the session ended when the credentials were actually rejected", () => {
    expectSaysSessionEnded(messageFor(new AuthExpiredError()));
  });

  it("tells transient and expired apart by type, not by message text", () => {
    // Both are plain Errors carrying developer-facing text, and neither message
    // is inspected. A reword of either message must not change what a user is
    // told, and the two must never collapse into one class.
    const transient = new AuthTransientError();
    const expired = new AuthExpiredError();

    expect(transient.message).toBe("Token refresh failed");
    expect(expired.message).toBe("Unauthorized");
    expect(messageFor(transient)).not.toBe(messageFor(expired));

    // A bare Error carrying the identical text gets neither sentence: only the
    // class decides.
    expect(messageFor(new Error("Token refresh failed"))).toBe(FALLBACK);
    expect(messageFor(new Error("Unauthorized"))).toBe(FALLBACK);
  });

  it("passes a backend detail through unchanged", () => {
    expect(messageFor(apiError(422, "Article is not ready to publish."))).toBe(
      "Article is not ready to publish.",
    );
  });

  it("falls back when a 4xx carries no usable detail", () => {
    expect(messageFor(apiError(404))).toBe(FALLBACK);
    expect(messageFor(apiError(400, { field: "title" }))).toBe(FALLBACK);
  });

  it("hides a 5xx detail behind a neutral sentence", () => {
    expect(messageFor(apiError(500, "IntegrityError at line 402"))).toBe(
      "Something went wrong at our end. Nothing was saved — try again in a moment.",
    );
  });

  it("treats a network TypeError as unreachable rather than as a bug", () => {
    // Chrome says "Failed to fetch", Safari "Load failed", Firefox something
    // else again. None of them belong on screen.
    expectSaysWorkIsSafe(messageFor(new TypeError("Failed to fetch")));
  });

  it("falls back to the caller's sentence for anything unrecognised", () => {
    expect(messageFor(new Error("boom"))).toBe(FALLBACK);
    expect(messageFor("a thrown string")).toBe(FALLBACK);
    expect(messageFor(undefined)).toBe(FALLBACK);
  });

  it("uses the caller's own sentence rather than a shared one", () => {
    expect(describeApiError(new Error("boom"), "Couldn't open this article.")).toBe(
      "Couldn't open this article.",
    );
  });
});
