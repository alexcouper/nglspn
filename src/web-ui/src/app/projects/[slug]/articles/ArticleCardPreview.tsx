"use client";

import { ArrowsPointingOutIcon } from "@heroicons/react/24/outline";
import { ArticleCard } from "@/components/ArticleCard";
import type { CropRect } from "@/components/CroppedImage";
import type { Article, ArticleListItem } from "@/lib/api";

const SUMMARY_MAX = 300;

interface Props {
  article: Article;
  summary: string;
  // The override being edited. Null means the card follows the hero framing.
  cardCrop: CropRect | null;
  onSummaryChange: (value: string) => void;
  onAdjustFraming: () => void;
  onResetFraming: () => void;
}

// ArticleCard takes a list item, so adapt. `summary` on a list item is already
// resolved server-side — mirror that here by falling back to summary_display,
// and the same for the card crop, which falls back to the derived rect.
export function toListItem(
  article: Article,
  summaryOverride?: string,
  cardCropOverride?: CropRect | null,
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
    card_crop: cardCropOverride ?? article.card_crop_display,
  } as ArticleListItem;
}

export function ArticleCardPreview({
  article,
  summary,
  cardCrop,
  onSummaryChange,
  onAdjustFraming,
  onResetFraming,
}: Props) {
  const item = toListItem(article, summary, cardCrop);
  const projectRef = article.project.slug ?? article.project.id;
  const href = `/projects/${projectRef}/articles/${article.slug ?? ""}`;
  const canFrame = !!article.hero_image?.width && !!article.hero_image?.height;

  return (
    // Summary first: it is the only text control here, and a full-width lead
    // card above it pushes it out of the dialog's scroll viewport entirely.
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

      {canFrame && (
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="text-muted-foreground">
            {cardCrop
              ? "Cards use their own framing."
              : "Cards follow the hero framing."}
          </span>
          <div className="flex items-center gap-2">
            {cardCrop && (
              <button
                onClick={onResetFraming}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Reset to match hero
              </button>
            )}
            <button
              onClick={onAdjustFraming}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-foreground hover:bg-muted transition-colors"
            >
              <ArrowsPointingOutIcon className="w-4 h-4" />
              Adjust framing
            </button>
          </div>
        </div>
      )}

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
