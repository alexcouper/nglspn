"use client";

import { CroppedImage, type CropRect } from "./CroppedImage";

interface Props {
  src: string | null | undefined;
  alt: string;
  // The stored framing. Null falls back to a 16:9 centre cover, which is what
  // every article looked like before cropping existed.
  crop?: CropRect | null;
  // Set on the one image that is above the fold — the lead card. Everything
  // else stays lazy.
  priority?: boolean;
  className?: string;
}

// The single definition of how an article's listing image is framed. The author
// picks the region in the listing-image wizard and it is frozen with the
// article, so the editor's preview and every card show the same region at the
// same shape — and because the box takes its aspect from the crop, that holds
// at any viewport width.
//
// Renders nothing without a source. An article needs no image, and a card with
// none gives the space to its headline rather than drawing a placeholder.
//
// Only original uploads and width-based variants are stored (see
// docs/image-performance-analysis.md), so the crop is applied at render.
export function ArticleListingImage({
  src,
  alt,
  crop,
  priority = false,
  className = "",
}: Props) {
  if (!src) return null;

  return (
    <CroppedImage
      src={src}
      alt={alt}
      crop={crop}
      priority={priority}
      className={className}
      // e2e reads the rendered aspect ratio off this to check that the framing
      // an author chose survived a save and a reload.
      testId="article-listing-image"
    />
  );
}
