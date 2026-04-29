import { afterEach, vi } from "vitest";

afterEach(() => {
  localStorage.clear();
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0].trim();
    if (name) {
      document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
