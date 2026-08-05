"use client";

import Link from "next/link";

import { GradientPlaceholder } from "@/components/GradientPlaceholder";

interface ProjectTileProps {
  /** Project id — seeds the gradient shown when there is no image. */
  id: string;
  href: string;
  imageUrl: string | null;
  title: string;
  tagline?: string | null;
  categoryName?: string | null;
  /** Read-only surface: no hover affordance, muted text. */
  dimmed?: boolean;
}

/**
 * The standard project card: image on top, text below.
 *
 * Takes plain values rather than an API type — the listing page and the
 * reviewer ballot are served by different response schemas and neither should
 * own the other's rendering.
 */
export function ProjectTile({
  id,
  href,
  imageUrl,
  title,
  tagline,
  categoryName,
  dimmed = false,
}: ProjectTileProps) {
  return (
    <Link href={href} className="flex w-full h-full">
      <div
        className={`card overflow-hidden flex flex-col w-full ${
          dimmed ? "opacity-75" : "card-interactive"
        }`}
      >
        <div className="relative aspect-[4/3]">
          {imageUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imageUrl}
                alt={title}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,0,0,0.15)] to-transparent" />
            </>
          ) : (
            <GradientPlaceholder id={id} className="w-full h-full" />
          )}
        </div>
        <div className="p-3.5 flex-1">
          {categoryName && (
            <span
              className={`text-[10px] font-semibold uppercase tracking-wider ${
                dimmed ? "text-muted-foreground" : "text-accent"
              }`}
            >
              {categoryName}
            </span>
          )}
          <h3
            className={`text-sm font-medium mt-0.5 line-clamp-2 ${
              dimmed ? "text-muted-foreground" : "text-foreground"
            }`}
          >
            {title}
          </h3>
          {tagline && (
            <p
              className={`text-xs mt-0.5 line-clamp-2 ${
                dimmed ? "text-muted-foreground/80" : "text-muted-foreground"
              }`}
            >
              {tagline}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
