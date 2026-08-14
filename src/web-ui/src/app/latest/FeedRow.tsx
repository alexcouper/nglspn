"use client";

import Link from "next/link";

import { ArticleListingImage } from "@/components/ArticleListingImage";
import type { FeedEntry } from "@/lib/api";
import { formatDate } from "@/lib/utils";

import { renderEntry } from "./feedEntry";

interface Props {
  entry: FeedEntry;
  /** The lead is the one row that gets the full-width treatment. */
  variant: "lead" | "row";
}

// One component for all three entry states. A bare event is the same row with
// less in it — no image, no standfirst — which is the point of modelling
// entries as stories rather than as articles-and-other-things.
export function FeedRow({ entry, variant }: Props) {
  const rendered = renderEntry(entry);
  const isLead = variant === "lead";

  const body = isLead ? (
    <>
      <ArticleListingImage
        src={rendered.imageUrl}
        alt=""
        crop={rendered.crop}
        priority
      />
      <div className="p-5">
        <Flag>{rendered.flag}</Flag>
        <h2 className="mt-1.5 text-2xl font-semibold text-foreground line-clamp-3">
          {rendered.headline}
        </h2>
        {rendered.summary && (
          <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
            {rendered.summary}
          </p>
        )}
        <Meta rendered={rendered} />
      </div>
    </>
  ) : (
    <div className="flex gap-4 p-4">
      {rendered.imageUrl && (
        <div className="w-28 shrink-0 sm:w-36">
          <ArticleListingImage
            src={rendered.imageUrl}
            alt=""
            crop={rendered.crop}
          />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <Flag>{rendered.flag}</Flag>
        <h3 className="mt-0.5 font-semibold text-foreground line-clamp-2">
          {rendered.headline}
        </h3>
        {rendered.summary && (
          <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
            {rendered.summary}
          </p>
        )}
        <Meta rendered={rendered} />
      </div>
    </div>
  );

  const className = `block rounded-lg border border-border bg-white overflow-hidden transition-colors ${
    rendered.href ? "hover:border-accent/50" : ""
  }`;

  return (
    <article className={className} data-testid={`feed-entry-${variant}`}>
      {rendered.href ? (
        <Link href={rendered.href} className="block">
          {body}
        </Link>
      ) : (
        body
      )}
    </article>
  );
}

function Flag({ children }: { children: string }) {
  return (
    <div className="text-xs font-semibold uppercase tracking-wide text-accent">
      {children}
    </div>
  );
}

function Meta({ rendered }: { rendered: ReturnType<typeof renderEntry> }) {
  const parts = [rendered.meta, formatDate(rendered.occurredAt)].filter(Boolean);
  return (
    <div className="mt-2 text-xs text-muted-foreground">{parts.join(" · ")}</div>
  );
}
