"use client";

import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArticleHeroImage } from "./ArticleHeroImage";

interface Props {
  article: ArticleListItem;
  // Supplied rather than derived from a project slug: a cross-project feed
  // builds its links differently.
  href: string;
  variant: "lead" | "grid";
}

const HEADLINE = {
  lead: "text-2xl font-semibold line-clamp-3",
  grid: "text-base font-semibold line-clamp-2",
} as const;

const SUMMARY = {
  lead: "line-clamp-2",
  grid: "line-clamp-3",
} as const;

export function ArticleCard({ article, href, variant }: Props) {
  const isLead = variant === "lead";

  return (
    <article className="rounded-lg border border-border bg-white overflow-hidden hover:border-accent/50 transition-colors">
      <Link href={href} className="block">
        <ArticleHeroImage
          src={article.hero_image_url}
          alt=""
          articleId={article.id}
          priority={isLead}
        />
        <div className={isLead ? "p-5" : "p-4"}>
          <div className="text-xs font-semibold uppercase tracking-wide text-accent">
            {article.channel.name}
            {article.published_at && (
              <span className="text-muted-foreground font-normal normal-case tracking-normal">
                {" · "}
                {formatDate(article.published_at)}
              </span>
            )}
          </div>
          <h3 className={`mt-1.5 text-foreground ${HEADLINE[variant]}`}>
            {article.title}
          </h3>
          {article.summary && (
            <p
              className={`mt-2 text-sm text-muted-foreground ${SUMMARY[variant]}`}
            >
              {article.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
