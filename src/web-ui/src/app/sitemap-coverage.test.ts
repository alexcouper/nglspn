import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import sitemap, { PUBLIC_STATIC_PAGES } from "@/app/sitemap";
import { SITE_URL } from "@/lib/constants";

const APP_DIR = path.resolve(__dirname);

// Routes that exist but deliberately stay out of the sitemap. Anything not
// listed here and not covered by another rule must appear in the sitemap, so
// adding a public page without listing it fails this suite rather than
// silently going unindexed.
const PRIVATE_ROUTES = [
  "/create",
  "/login",
  "/register",
  "/onboarding",
  "/verify-email",
  "/notifications",
  "/profile",
  "/profile/following",
  "/profile/settings",
  "/my-projects",
  "/my-reviews",
];

// The legacy listing kept around since the /projects redesign. Unreachable
// from the live UI and slated for removal; it must never be advertised.
const LEGACY_ROUTES = ["/old/projects"];

// Guide routes are generated from the guide content, not hand-listed, and
// src/lib/guides.test.tsx already asserts every guide URL reaches the sitemap.
const isGuideRoute = (route: string) => /^(\/is)?\/guides$/.test(route);

const isDynamic = (route: string) => route.includes("[");

const isRedirectOnly = (route: string) => {
  const file = path.join(APP_DIR, route, "page.tsx");
  const source = readFileSync(file, "utf8");
  return source.includes("redirect(") && !source.includes("export default async");
};

function findPageRoutes(dir: string, route = ""): string[] {
  const routes: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      routes.push(...findPageRoutes(path.join(dir, entry.name), `${route}/${entry.name}`));
    } else if (entry.name === "page.tsx") {
      routes.push(route === "" ? "/" : route);
    }
  }
  return routes;
}

function routesRequiringSitemapEntry(): string[] {
  return findPageRoutes(APP_DIR).filter(
    (route) =>
      route !== "/" &&
      !isDynamic(route) &&
      !isGuideRoute(route) &&
      !PRIVATE_ROUTES.includes(route) &&
      !LEGACY_ROUTES.includes(route) &&
      !isRedirectOnly(route),
  );
}

const sitemapPaths = () => sitemap().map((entry) => entry.url.replace(SITE_URL, ""));

describe("sitemap coverage", () => {
  it("advertises every public page in the app router", () => {
    expect([...sitemapPaths()].sort()).toEqual(
      expect.arrayContaining(routesRequiringSitemapEntry().sort()),
    );
  });

  it("lists no page that has been deleted or made private", () => {
    const existing = findPageRoutes(APP_DIR);
    for (const route of PUBLIC_STATIC_PAGES) {
      expect(existing, `${route} is in the sitemap but has no page.tsx`).toContain(route);
      expect(PRIVATE_ROUTES, `${route} is both public and private`).not.toContain(route);
    }
  });

  it("keeps private, legacy and redirect-only routes out", () => {
    const advertised = sitemapPaths();
    for (const route of [...PRIVATE_ROUTES, ...LEGACY_ROUTES, "/why", "/prizes"]) {
      expect(advertised, `${route} must not be advertised`).not.toContain(route);
    }
  });

  it("emits absolute URLs under a single configured origin", () => {
    for (const entry of sitemap()) {
      expect(entry.url.startsWith(`${SITE_URL}/`)).toBe(true);
    }
  });
});
