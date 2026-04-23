export const EDIT_MODE_COOKIE = "nglspn-edit-mode";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

export function setEditModeCookie(on: boolean): void {
  if (typeof document === "undefined") return;
  if (on) {
    document.cookie =
      `${EDIT_MODE_COOKIE}=1; path=/; max-age=${MAX_AGE_SECONDS}; samesite=lax`;
  } else {
    document.cookie = `${EDIT_MODE_COOKIE}=; path=/; max-age=0; samesite=lax`;
  }
}

export function readEditModeCookieClient(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie
    .split("; ")
    .some((pair) => pair === `${EDIT_MODE_COOKIE}=1`);
}
