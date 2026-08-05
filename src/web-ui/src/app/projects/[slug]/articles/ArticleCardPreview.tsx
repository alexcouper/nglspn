"use client";

import { ArticleCard } from "@/components/ArticleCard";
import type { Article, ArticleListItem } from "@/lib/api";

const SUMMARY_MAX = 300;

interface Props {
  article: Article;
  summary: string;
  onSummaryChange: (value: string) => void;
}

// ArticleCard takes a list item, so adapt. `summary` on a list item is already
// resolved server-side — mirror that here by falling back to summary_display.
export function toListItem(
  article: Article,
  summaryOverride?: string,
): ArticleListItem {
  const summary = summaryOverride ?? article.summary;
  return {
    id: article.id,
    title: article.title,
    summary: summary || article.summary_display,
    slug: article.slug,
    state: article.state,
    published_at: article.published_at,
    global_visibility: article.global_visibility,
    channel: article.channel,
    hero_image_url: article.hero_image_url,
  } as ArticleListItem;
}

export function ArticleCardPreview({
  article,
  summary,
  onSummaryChange,
}: Props) {
  const item = toListItem(article, summary);
  const projectRef = article.project.slug ?? article.project.id;
  const href = `/projects/${projectRef}/articles/${article.slug ?? ""}`;

  return (
    // Summary first: it is the only control here, and a full-width lead card
    // above it pushes it out of the dialog's scroll viewport entirely.
    <div className="space-y-5">
      <div>
        <label
          htmlFor="article-summary"
          className="block text-sm font-medium text-foreground"
        >
          Summary
        </label>
        <textarea
          id="article-summary"
          value={summary}
          placeholder={article.summary_display}
          maxLength={SUMMARY_MAX}
          rows={3}
          onChange={(e) => onSummaryChange(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
        />
        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
          <span>Leave empty to use the start of the article.</span>
          <span>
            {summary.length}/{SUMMARY_MAX}
          </span>
        </div>
      </div>

      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
          As the lead story
        </div>
        <ArticleCard article={item} href={href} variant="lead" />
      </div>

      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
          In the grid
        </div>
        <div className="max-w-sm">
          <ArticleCard article={item} href={href} variant="grid" />
        </div>
      </div>
    </div>
  );
}
