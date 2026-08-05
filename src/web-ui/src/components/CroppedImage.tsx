"use client";

import type { CSSProperties } from "react";

// Deliberately structural rather than imported from the generated API types:
// this component and the cropper built on it are not article-specific, and a
// crop is the same five numbers wherever it comes from. The API's own CropRect
// is identical in shape, so values pass either way without conversion.
export interface CropRect {
  // Normalised against the source image. Values outside 0–1 are legal and mean
  // the crop extends past the edge of the image — see CROP_BACKGROUND.
  x: number;
  y: number;
  w: number;
  h: number;
  // The rendered aspect as a decimal. Derivable from the rect plus the source
  // dimensions, but carried explicitly so a consumer can reserve its box before
  // it knows anything about the source.
  ratio: number;
}

// What a crop-less image gets: the framing every article had before crops
// existed. Kept as a constant so the fallback is one decision, not four.
export const DEFAULT_RATIO = 16 / 9;

// Shown wherever a crop extends past the edge of its source. One shared value
// so the cropper's preview and the rendered result cannot disagree about what
// the author was promised.
export const CROP_BACKGROUND = "#ffffff";

interface Props {
  src: string;
  alt: string;
  crop: CropRect | null | undefined;
  // Set on the one image above the fold — the lead card, or the hero on an
  // article page. Everything else stays lazy.
  priority?: boolean;
  className?: string;
  testId?: string;
}

// Applies a stored crop with CSS rather than a cut file: the box takes the
// crop's aspect and the image is scaled and offset inside it so the selected
// region fills it. Re-cropping is four numbers, so it costs nothing.
//
// The same arithmetic covers a crop that runs past the image: `w > 1` makes the
// image narrower than the box and a negative `x` pushes it inwards, leaving
// CROP_BACKGROUND showing at the edges.
//
// With no crop this is the old behaviour — a 16:9 centre cover — which is why
// articles predating cropping need no backfill.
export function CroppedImage({
  src,
  alt,
  crop,
  priority = false,
  className = "",
  testId,
}: Props) {
  const loading = priority ? "eager" : "lazy";

  return (
    <div
      data-testid={testId}
      style={{
        aspectRatio: String(crop ? crop.ratio : DEFAULT_RATIO),
        backgroundColor: CROP_BACKGROUND,
      }}
      className={`relative overflow-hidden ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        loading={loading}
        decoding="async"
        style={crop ? insetStyle(crop) : undefined}
        className={crop ? "absolute" : "absolute inset-0 h-full w-full object-cover"}
      />
    </div>
  );
}

// `maxWidth: "none"` is load-bearing. A global `img { max-width: 100% }` reset
// would cap the scaled image and silently shift the crop, so it is set inline
// where a stylesheet cannot beat it.
function insetStyle(crop: CropRect): CSSProperties {
  return {
    width: `${100 / crop.w}%`,
    height: `${100 / crop.h}%`,
    left: `${(-crop.x / crop.w) * 100}%`,
    top: `${(-crop.y / crop.h) * 100}%`,
    maxWidth: "none",
  };
}
