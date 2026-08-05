"use client";

import { CroppedImage, DEFAULT_RATIO, type CropRect } from "./CroppedImage";
import { GradientPlaceholder } from "./GradientPlaceholder";

interface Props {
  src: string | null | undefined;
  alt: string;
  articleId: string;
  // The stored framing. Null falls back to a 16:9 centre cover, which is what
  // every article looked like before cropping existed.
  crop?: CropRect | null;
  // Set on the one hero that is above the fold — the lead card, or the hero on
  // an article page. Everything else stays lazy.
  priority?: boolean;
  className?: string;
}

// The single definition of how an article hero is framed. The author picks the
// ratio in the crop dialog and it is frozen with the article, so the editor,
// the article page and every card show the same region at the same shape — and
// because the box takes its aspect from the crop, that holds at any viewport
// width.
//
// Only original uploads and width-based variants are stored (see
// docs/image-performance-analysis.md), so the crop is applied at render.
export function ArticleHeroImage({
  src,
  alt,
  articleId,
  crop,
  priority = false,
  className = "",
}: Props) {
  if (!src) {
    return (
      // No `w-full` here: in block context the div already fills its container,
      // and a flex-row caller passes its own width (which `w-full` would beat,
      // since Tailwind precedence is stylesheet order, not class-attribute order).
      <div
        data-testid="article-hero"
        style={{ aspectRatio: String(crop ? crop.ratio : DEFAULT_RATIO) }}
        className={`relative overflow-hidden bg-muted ${className}`}
      >
        <GradientPlaceholder id={articleId} className="absolute inset-0" />
      </div>
    );
  }

  return (
    <CroppedImage
      src={src}
      alt={alt}
      crop={crop}
      priority={priority}
      className={className}
      // e2e reads the rendered aspect ratio off this to check that the framing
      // an author chose survived a save and a reload.
      testId="article-hero"
    />
  );
}
