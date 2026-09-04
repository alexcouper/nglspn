"use client";

import { useState, type ReactNode } from "react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import type { GalleryImage } from "./gallery-mdast";

interface Props {
  images: readonly GalleryImage[];
  /**
   * Rendered over the top-right corner of the current image. The editor puts
   * its per-image delete and nudge buttons here; the read view passes
   * nothing.
   */
  controls?: (index: number) => ReactNode;
  /** Rendered under the caption. The editor's drop hint uses this. */
  footer?: ReactNode;
}

/**
 * One image at a time, with prev/next arrows, a dot per image and the alt
 * text as a caption.
 *
 * Shared by the read view (`ArticleRenderContent`) and the editor
 * (`GalleryDirectiveDescriptor`) so the two cannot drift apart.
 */
export function ArticleGallery({ images, controls, footer }: Props) {
  const [index, setIndex] = useState(0);

  // Deleting an image in the editor can leave `index` past the end. Adjusting
  // during render (rather than in an effect) keeps the stale index from
  // reappearing if the list grows again.
  const lastIndex = Math.max(images.length - 1, 0);
  if (index > lastIndex) setIndex(lastIndex);
  const current = Math.min(index, lastIndex);

  if (images.length === 0) {
    return controls ? (
      <div className="my-6 rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
        Empty gallery
      </div>
    ) : null;
  }

  const image = images[current];
  const atStart = current === 0;
  const atEnd = current === images.length - 1;

  return (
    <div className="article-gallery my-6 rounded-lg border border-border bg-muted/30">
      <div className="relative">
        {/* The minimum height keeps the vertically-centred arrows clear of
            the controls in the top-right corner. Without it a short image
            puts the right arrow on top of them and it takes the clicks. */}
        <div
          className="flex min-h-40 items-center justify-center px-10 py-4"
          aria-live="polite"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image.src} alt={image.alt} title={image.title} />
        </div>

        {controls && (
          <div className="absolute top-2 right-2 z-10 flex items-center gap-1">
            {controls(current)}
          </div>
        )}

        <GalleryArrow
          side="left"
          label="Previous image"
          disabled={atStart}
          onClick={() => setIndex(current - 1)}
        />
        <GalleryArrow
          side="right"
          label="Next image"
          disabled={atEnd}
          onClick={() => setIndex(current + 1)}
        />
      </div>

      <div className="flex flex-wrap items-center justify-center gap-1.5 px-3 pb-2">
        {images.map((_, position) => (
          <button
            key={position}
            type="button"
            aria-label={`Show image ${position + 1}`}
            aria-current={position === current}
            onClick={() => setIndex(position)}
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              position === current
                ? "bg-foreground"
                : "bg-border hover:bg-muted-foreground"
            }`}
          />
        ))}
      </div>

      <div className="px-4 pb-3 text-center text-sm text-muted-foreground">
        <span className="tabular-nums">
          {current + 1} / {images.length}
        </span>
        {image.alt && <span className="ml-2">{image.alt}</span>}
      </div>

      {footer}
    </div>
  );
}

function GalleryArrow({
  side,
  label,
  disabled,
  onClick,
}: {
  side: "left" | "right";
  label: string;
  disabled: boolean;
  onClick: () => void;
}) {
  const Icon = side === "left" ? ChevronLeftIcon : ChevronRightIcon;
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={`absolute top-1/2 -translate-y-1/2 ${
        side === "left" ? "left-1" : "right-1"
      } rounded-full border border-border bg-white p-1.5 text-foreground shadow-sm transition-opacity hover:bg-muted disabled:opacity-30`}
    >
      <Icon className="h-5 w-5" />
    </button>
  );
}
