export const SITE_EMAIL = "alex@naglasupan.is";
export const SITE_DISCORD_URL = "https://discord.gg/KX7qmrwP7x";

// Every absolute URL the site emits about itself — canonicals, hreflang
// alternates, social card URLs, JSON-LD ids, robots.txt and the sitemap. A
// deployment that is not production sets NEXT_PUBLIC_SITE_URL, otherwise it
// advertises production URLs for pages that only exist on that host. No
// trailing slash: callers append paths that start with one.
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://naglasupan.is";
