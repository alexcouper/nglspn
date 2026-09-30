import type { MetadataRoute } from "next";
import { GUIDE_SITE_URL } from "@/lib/guides";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${GUIDE_SITE_URL}/sitemap.xml`,
  };
}
