"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { articleHrefOf } from "./container";
import { ArticleCard } from "@/components/ArticleCard";
import type { CropRect } from "@/components/CroppedImage";
import type { Article, ArticleListItem } from "@/lib/api";

type Variant = "lead" | "grid";

const VARIANTS: Variant[] = ["lead", "grid"];

interface Props {
  article: Article;
  // The unsaved values, so the preview tracks the panel's controls rather than
  // the last save. `summary` still falls back to summary_display, which only
  // Python can compute — that is why the panel saves before showing this.
  summary: string;
  imageUrl: string | null;
  crop: CropRect | null;
}

// ArticleCard takes a list item, so adapt.
export function toListItem(
  article: Article,
  summaryOverride?: string,
  imageUrlOverride?: string | null,
  cropOverride?: CropRect | null,
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
    is_globally_visible: article.is_globally_visible,
    channel: article.channel,
    listing_image_url:
      imageUrlOverride !== undefined
        ? imageUrlOverride
        : article.listing_image_url,
    listing_crop:
      cropOverride !== undefined ? cropOverride : article.listing_crop,
  };
}

// One variant at a time. Stacking both showed the author the same article twice
// in one viewport, which is what this replaced.
export function ArticleCardPreview({ article, summary, imageUrl, crop }: Props) {
  const t = useTranslations("articles.cardPreview");
  const [variant, setVariant] = useState<Variant>("lead");
  const item = toListItem(article, summary, imageUrl, crop);
  // A draft has no slug yet, and this tab is used mostly on drafts. Linking
  // anyway would send the author to /articles/, so the preview goes inert.
  const href = articleHrefOf(article) ?? undefined;

  return (
    <div>
      <div role="tablist" aria-label={t("tablistLabel")} className="flex gap-1">
        {VARIANTS.map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={variant === key}
            onClick={() => setVariant(key)}
            className={`rounded-t-lg border-b-2 px-3 py-1.5 text-sm transition-colors ${
              variant === key
                ? "border-accent font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(key)}
          </button>
        ))}
      </div>

      <div className="mt-3">
        {/* A grid card at full width is not what a grid card looks like. */}
        <div className={variant === "grid" ? "max-w-sm" : undefined}>
          <ArticleCard article={item} href={href} variant={variant} />
        </div>
      </div>
    </div>
  );
}
