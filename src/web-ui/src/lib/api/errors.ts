import { ApiRequestError, AuthExpiredError, AuthTransientError } from "./base";

// The backend's `detail` is written for the person reading it. A thrown Error's
// message is written for whoever is reading the console. Only the first kind
// gets shown to a user.
//
// Import this from "@/lib/api/errors" rather than through the "@/lib/api"
// barrel: tests that mock the barrel wholesale would otherwise get a stub, and
// the `instanceof` narrowing below would silently fall through to the fallback.

const UNREACHABLE =
  "Couldn't reach the server. Nothing was sent — your work is still here. Try again.";
const SESSION_ENDED = "Your session has ended. Sign in again to continue.";
const SERVER_FAULT =
  "Something went wrong at our end. Nothing was saved — try again in a moment.";

export function describeApiError(err: unknown, fallback: string): string {
  // Transient and expired are told apart by TYPE, not by message text. Keep it
  // that way: base.ts deliberately keeps the tokens on a transient refresh
  // failure, so telling the user to sign in again here would be wrong, and
  // collapsing the two classes "for tidiness" would reintroduce that lie.
  if (err instanceof AuthTransientError) return UNREACHABLE;
  // Genuinely logged out, and useRequireAuth is already routing to /login. This
  // is a flash before the route changes, so it only has to be true.
  if (err instanceof AuthExpiredError) return SESSION_ENDED;
  if (err instanceof ApiRequestError) {
    if (err.status >= 500) return SERVER_FAULT;
    // Read `body.detail` rather than `err.message`, which falls back to the
    // useless "Request failed".
    return typeof err.body.detail === "string" ? err.body.detail : fallback;
  }
  // fetch() rejects with a TypeError when the network is gone. The message is
  // browser-specific ("Failed to fetch", "Load failed", …) and means nothing to
  // a person.
  if (err instanceof TypeError) return UNREACHABLE;
  return fallback;
}
