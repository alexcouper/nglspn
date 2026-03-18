import type { User } from "@/lib/api";

const DEFAULT_DESTINATION = "/my-projects";

/** Pages that should never be returned to after login. */
const AUTH_PAGES = ["/login", "/register", "/verify-email", "/onboarding"];

function isSafeRedirect(url: string): boolean {
  return url.startsWith("/") && !url.startsWith("//") && !AUTH_PAGES.includes(url) && url !== "/";
}

export function getPostAuthDestination(user: User, next?: string | null): string {
  if (user.pending_onboarding_steps.length > 0) {
    const params = next ? `?next=${encodeURIComponent(next)}` : "";
    return `/onboarding${params}`;
  }
  if (next && isSafeRedirect(next)) {
    return next;
  }
  return DEFAULT_DESTINATION;
}

export function buildLoginPath(returnTo: string): string {
  if (isSafeRedirect(returnTo)) {
    return `/login?next=${encodeURIComponent(returnTo)}`;
  }
  return "/login";
}
