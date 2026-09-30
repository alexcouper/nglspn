import type { MetadataRoute } from "next";
import { guides } from "@/content/guides";
import { SITE_URL } from "@/lib/constants";
import { guideUrl } from "@/lib/guides";

// Public pages with a fixed path. Every other page under src/app is either
// derived below (the guides), addressed by a dynamic segment, private, or a
// redirect — sitemap-coverage.test.ts walks the route tree and fails if a new
// page is none of those and is missing from here.
export const PUBLIC_STATIC_PAGES = [
  "/projects",
  "/competitions",
  "/latest",
  "/about",
  "/about/why",
  "/about/prizes",
  "/about/contact",
  "/privacy",
];

// Projects, articles and competitions are addressed by dynamic segments and
// are not enumerated yet — see issue #96. No private drafts or account routes
// belong in this sitemap.
export default function sitemap(): MetadataRoute.Sitemap {
  const guideEntries = [{ slug: "", updated: undefined }, ...guides];
  return [
    ...PUBLIC_STATIC_PAGES.map((path) => ({ url: `${SITE_URL}${path}` })),
    ...(["en", "is"] as const).flatMap((language) =>
      guideEntries.map((guide) => ({
        url: `${SITE_URL}${guideUrl(language, guide.slug)}`,
        ...(guide.updated ? { lastModified: guide.updated } : {}),
        alternates: {
          languages: {
            en: `${SITE_URL}${guideUrl("en", guide.slug)}`,
            is: `${SITE_URL}${guideUrl("is", guide.slug)}`,
          },
        },
      })),
    ),
  ];
}
