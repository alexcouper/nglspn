"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ArticleCard } from "@/components/ArticleCard";
import type { Article, ArticleListItem } from "@/lib/api";
import { ArticleRenderContent } from "./ArticleRenderContent";
import { articleHrefOf, type Container } from "./container";
import { resolveOrigin } from "./origin";

type View = "article" | "lead" | "grid";

const VIEWS: View[] = ["article", "lead", "grid"];

interface Props {
  // The saved article: the page saves before switching to the preview, so
  // the body and the derived summary are the server's and not the editor's.
  article: Article;
  container: Container;
}

// ArticleCard takes a list item, so adapt.
export function toListItem(article: Article): ArticleListItem {
  return {
    id: article.id,
    title: article.title,
    summary: article.summary || article.summary_display,
    slug: article.slug,
    state: article.state,
    published_at: article.published_at,
    global_visibility: article.global_visibility,
    is_globally_visible: article.is_globally_visible,
    channel: article.channel,
    listing_image_url: article.listing_image_url,
    listing_crop: article.listing_crop,
  };
}

// The three places an article shows up, one at a time: its own page, and the
// two card variants on listings.
export function ArticlePreview({ article, container }: Props) {
  const t = useTranslations("articles.preview");
  const [view, setView] = useState<View>("article");
  // Spelled out rather than t(`${view}`): a template-literal key is not
  // checked against the messages, so `tsc` fails on a missing message and a
  // missing view alike.
  const labels: Record<View, string> = {
    article: t("article"),
    lead: t("lead"),
    grid: t("grid"),
  };
  // A draft has no slug yet, and this is used mostly on drafts. Linking
  // anyway would send the author to /articles/, so the card goes inert.
  const href = articleHrefOf(article) ?? undefined;

  return (
    <div>
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <div role="tablist" aria-label={t("tablistLabel")} className="flex gap-1">
          {VIEWS.map((key) => (
            <button
              key={key}
              role="tab"
              aria-selected={view === key}
              onClick={() => setView(key)}
              className={`border-b-2 px-3 py-2 text-sm transition-colors ${
                view === key
                  ? "border-accent font-medium text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {labels[key]}
            </button>
          ))}
        </div>
      </div>

      {view === "article" ? (
        <div className="mt-4 bg-white border-y border-border" data-testid="preview-article">
          <ArticleRenderContent
            container={container}
            article={article}
            origin={resolveOrigin(undefined, container)}
            onward={null}
            articleCount={0}
            channelCount={0}
            preview
          />
        </div>
      ) : (
        <div className="mt-4 max-w-4xl mx-auto px-4 sm:px-6">
          {/* A grid card at full width is not what a grid card looks like. */}
          <div className={view === "grid" ? "max-w-sm" : undefined}>
            <ArticleCard article={toListItem(article)} href={href} variant={view} />
          </div>
        </div>
      )}
    </div>
  );
}
