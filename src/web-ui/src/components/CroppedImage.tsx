"use client";

import type { CSSProperties } from "react";
import type { components } from "@/lib/api-types";

export type CropRect = components["schemas"]["CropRect"];

// What a crop-less image gets: the framing every article had before crops
// existed. Kept as a constant so the fallback is one decision, not four.
export const DEFAULT_RATIO = 16 / 9;

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
// crop's aspect and the image is scaled up and offset inside it so the selected
// region exactly fills it. Re-cropping is four numbers, so it costs nothing.
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
      style={{ aspectRatio: String(crop ? crop.ratio : DEFAULT_RATIO) }}
      className={`relative overflow-hidden bg-muted ${className}`}
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
