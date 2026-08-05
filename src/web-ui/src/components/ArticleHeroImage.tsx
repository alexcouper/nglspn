"use client";

import { GradientPlaceholder } from "./GradientPlaceholder";

interface Props {
  src: string | null | undefined;
  alt: string;
  articleId: string;
  // Set on the one hero that is above the fold — the lead card, or the hero on
  // an article page. Everything else stays lazy.
  priority?: boolean;
  className?: string;
}

// The single definition of how an article hero is framed. A fixed 16:9 crop
// means a wide upload lands as-is and a portrait upload gives a centre band,
// and — because the card, the listing lead and the article page all use this —
// what the author frames is what every surface shows.
//
// Only original uploads are stored, with no size variants (see
// docs/image-performance-analysis.md), so these are full-resolution files.
export function ArticleHeroImage({
  src,
  alt,
  articleId,
  priority = false,
  className = "",
}: Props) {
  return (
    // No `w-full` here: in block context the div already fills its container,
    // and a flex-row caller passes its own width (which `w-full` would beat,
    // since Tailwind precedence is stylesheet order, not class-attribute order).
    <div
      className={`relative aspect-[16/9] overflow-hidden bg-muted ${className}`}
    >
      {src ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={src}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <GradientPlaceholder id={articleId} className="absolute inset-0" />
      )}
    </div>
  );
}
