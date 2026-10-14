import type { Project } from "@/lib/api";

export interface Origin {
  href: string;
  label: string;
}

/**
 * The places worth naming in the back control, keyed by the `from` parameter
 * the linking page adds.
 *
 * Deliberately short. Every other way into an article — a shared URL, a
 * notification, a search result, a profile — falls back to the project, which
 * is where the article lives and is therefore never a lie. Adding an origin is
 * one entry here plus the parameter on the link.
 */
// A Map rather than an object literal: `from` is attacker-controlled, and a
// plain object answers to `constructor` and `toString` with something truthy.
const ORIGINS = new Map<string, Origin>([
  ["latest", { href: "/latest", label: "Latest" }],
]);

/** The parameter name, so the linking side cannot drift from the reading side. */
export const ORIGIN_PARAM = "from";

/**
 * Where "back" goes and what it is called.
 *
 * Server-rendered from the query string rather than read from
 * `document.referrer`, which is not available while the page is being rendered
 * and is wrong after a reload.
 */
export function resolveOrigin(
  from: string | string[] | undefined,
  project: Project,
): Origin {
  const key = Array.isArray(from) ? from[0] : from;
  const named = key ? ORIGINS.get(key) : undefined;
  if (named) return named;

  return {
    href: `/projects/${project.slug ?? project.id}#articles`,
    label: project.title,
  };
}

/** Appends the origin to an article link. Used by the pages that list articles. */
export function withOrigin(href: string, from: string): string {
  return `${href}?${ORIGIN_PARAM}=${encodeURIComponent(from)}`;
}
