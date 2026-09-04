"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { sampleEdgeColor, type EdgeColor } from "./gallery-edge-color";
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
 * text as a caption. The space around the image takes the image's own edge
 * colour, so an export that carries its own background does not draw a box
 * inside the card.
 *
 * Shared by the read view (`ArticleRenderContent`) and the editor
 * (`GalleryDirectiveDescriptor`) so the two cannot drift apart.
 */
export function ArticleGallery({ images, controls, footer }: Props) {
  const [index, setIndex] = useState(0);

  // Held across a change of image rather than cleared, because the browser
  // keeps painting the outgoing image until the incoming one decodes, and
  // that image's colour is still the right one to sit behind it.
  const [fill, setFill] = useState<EdgeColor | null>(null);

  // Reading pixels back needs the image fetched anonymously, which the CDN
  // allows for the site's own origin. Somewhere it does not — a preview
  // deployment on another host — the request fails and every image is
  // refetched without the attribute. A missing background beats a broken
  // image. Origin-wide, so one refusal settles it for the whole gallery.
  const [corsRefused, setCorsRefused] = useState(false);

  const imageRef = useRef<HTMLImageElement>(null);

  // Deleting an image in the editor can leave `index` past the end. Adjusting
  // during render (rather than in an effect) keeps the stale index from
  // reappearing if the list grows again.
  const lastIndex = Math.max(images.length - 1, 0);
  if (index > lastIndex) setIndex(lastIndex);
  const current = Math.min(index, lastIndex);
  const src = images[current]?.src;

  // Cached images are already complete when the effect runs and never emit
  // `load`, hence the two paths.
  useEffect(() => {
    const img = imageRef.current;
    if (!img || !src) return;
    const read = () => setFill(sampleEdgeColor(img));
    if (img.complete) {
      read();
      return;
    }
    img.addEventListener("load", read);
    return () => img.removeEventListener("load", read);
  }, [src]);

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

  // On a filled card the border would read as a halo, and the slate caption
  // would sit on whatever the image's background happens to be.
  const onDark = fill?.isDark ?? false;
  const cardClass = fill
    ? onDark
      ? "border-white/15"
      : "border-black/10"
    : "border-border bg-muted/30";
  const captionClass = onDark ? "text-white/70" : "text-muted-foreground";

  return (
    <div
      className={`article-gallery my-6 rounded-lg border ${cardClass}`}
      style={fill ? { backgroundColor: fill.css } : undefined}
    >
      <div className="relative">
        {/* The minimum height keeps the vertically-centred arrows clear of
            the controls in the top-right corner. Without it a short image
            puts the right arrow on top of them and it takes the clicks. */}
        <div
          className="flex min-h-40 items-center justify-center px-10 py-4"
          aria-live="polite"
        >
          {/* Keyed on the CORS mode alone, not on the src: remounting per
              image would blank the box between images, where reusing the
              node leaves the outgoing image painted until the next decodes. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={corsRefused ? "same-origin" : "anonymous"}
            ref={imageRef}
            crossOrigin={corsRefused ? undefined : "anonymous"}
            onError={() => setCorsRefused(true)}
            src={image.src}
            alt={image.alt}
            title={image.title}
          />
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

      <div className="flex flex-wrap items-center justify-center gap-1.5 px-3 py-3">
        {images.map((_, position) => (
          <button
            key={position}
            type="button"
            aria-label={`Show image ${position + 1}`}
            aria-current={position === current}
            onClick={() => setIndex(position)}
            className={`h-1.5 w-1.5 rounded-full transition-colors ${dotClass(
              position === current,
              onDark,
            )}`}
          />
        ))}
      </div>

      <div className={`px-4 pb-3 text-center text-sm ${captionClass}`}>
        <span className="tabular-nums">
          {current + 1} / {images.length}
        </span>
        {image.alt && <span className="ml-2">{image.alt}</span>}
      </div>

      {footer}
    </div>
  );
}

function dotClass(isCurrent: boolean, onDark: boolean) {
  if (onDark) return isCurrent ? "bg-white" : "bg-white/30 hover:bg-white/60";
  return isCurrent ? "bg-foreground" : "bg-border hover:bg-muted-foreground";
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
