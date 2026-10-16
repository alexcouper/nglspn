import { type Container, containerArticlesHref, containerTitle } from "./container";

export type Origin =
  | { kind: "latest"; href: string }
  | { kind: "container"; href: string; title: string };

// A Map rather than an object literal: `from` is attacker-controlled, and a
// plain object answers to `constructor` and `toString` with something truthy.
const ORIGINS = new Map<string, Origin>([
  ["latest", { kind: "latest", href: "/latest" }],
]);

export const ORIGIN_PARAM = "from";

/** Where the back control goes. Anything unrecognised falls back to the
 *  article's container: its project, or its author's profile. */
export function resolveOrigin(
  from: string | string[] | undefined,
  container: Container,
): Origin {
  const key = Array.isArray(from) ? from[0] : from;
  const named = key ? ORIGINS.get(key) : undefined;
  if (named) return named;

  return {
    kind: "container",
    href: containerArticlesHref(container),
    title: containerTitle(container),
  };
}

export function withOrigin(href: string, from: string): string {
  return `${href}?${ORIGIN_PARAM}=${encodeURIComponent(from)}`;
}
