import type { MetadataRoute } from "next";
import { guides } from "@/content/guides";
import { GUIDE_SITE_URL, guideUrl } from "@/lib/guides";

// Public static pages. Project and article discovery also happens through the
// directory; no private drafts or account routes belong in this sitemap.
export default function sitemap(): MetadataRoute.Sitemap {
  const publicPages = ["/projects", "/competitions", "/about", "/about/why", "/about/prizes", "/about/contact", "/privacy"];
  const guideEntries = [{ slug: "", updated: undefined }, ...guides];
  return [
    ...publicPages.map((path) => ({ url: `${GUIDE_SITE_URL}${path}` })),
    ...(["en", "is"] as const).flatMap((language) => guideEntries.map((guide) => ({
      url: `${GUIDE_SITE_URL}${guideUrl(language, guide.slug)}`,
      ...(guide.updated ? { lastModified: guide.updated } : {}),
      alternates: {
        languages: {
          en: `${GUIDE_SITE_URL}${guideUrl("en", guide.slug)}`,
          is: `${GUIDE_SITE_URL}${guideUrl("is", guide.slug)}`,
        },
      },
    }))),
  ];
}
