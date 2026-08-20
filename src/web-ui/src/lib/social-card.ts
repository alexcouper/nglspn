import type { Metadata } from "next";

// The fallback card image: a page with no image of its own is still branded
// rather than blank. Relative, so `metadataBase` in the root layout makes it
// absolute.
export const SITE_LOGO_PATH = "/icons/app/logo.png";
export const SITE_NAME = "naglasúpan";

interface SocialCardInput {
  title: string;
  description?: string;
  // Absolute page URL. Omitted where the canonical URL is not worth deriving.
  url?: string;
  type?: "website" | "article";
  // The page's own image, if it has one; `null`/`undefined` falls back to the
  // site logo.
  imageUrl?: string | null;
  imageWidth?: number;
  imageHeight?: number;
}

// Both halves of a link preview, always together.
//
// Next merges page metadata into the root layout's shallowly: a page that sets
// `openGraph` but not `twitter` keeps the root's `twitter` tags verbatim, so
// its card advertises the site logo under the site's title. Discord, Slack and
// X all prefer the twitter tags when both are present, which is how an article
// with a perfectly good `og:image` still unfurled as the naglasúpan logo
// (issue #86). Spreading this into a page's metadata sets both, or neither.
export function socialCard({
  title,
  description,
  url,
  type = "website",
  imageUrl,
  imageWidth,
  imageHeight,
}: SocialCardInput): Pick<Metadata, "openGraph" | "twitter"> {
  const image = imageUrl || SITE_LOGO_PATH;
  return {
    openGraph: {
      type,
      siteName: SITE_NAME,
      ...(url && { url }),
      title,
      description,
      images: [
        {
          url: image,
          ...(imageUrl && imageWidth && { width: imageWidth }),
          ...(imageUrl && imageHeight && { height: imageHeight }),
          alt: imageUrl ? title : SITE_NAME,
        },
      ],
    },
    twitter: {
      // The logo is a square mark: blown up to a large card it is mostly
      // whitespace, so only a real page image earns the big treatment.
      card: imageUrl ? "summary_large_image" : "summary",
      title,
      description,
      images: [image],
    },
  };
}
