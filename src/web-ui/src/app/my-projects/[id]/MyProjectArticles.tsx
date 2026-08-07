"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusIcon } from "@heroicons/react/24/outline";
import { ArticleListingImage } from "@/components/ArticleListingImage";
import type { ArticleListItem } from "@/lib/api";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface Props {
  projectSlugOrId: string;
}

function publishedAtMs(article: ArticleListItem): number {
  return article.published_at ? new Date(article.published_at).getTime() : 0;
}

// Drafts first (`updated_at` would be more accurate than `created_at`-style
// fields the list endpoint exposes today, but we don't get an `updated_at` on
// the list item shape — drafts are typically few enough that ordering between
// them isn't critical). Then published articles by `published_at` desc.
function sortDraftsFirst(
  articles: ArticleListItem[],
): ArticleListItem[] {
  return [...articles].sort((a, b) => {
    const aDraft = a.state !== "published";
    const bDraft = b.state !== "published";
    if (aDraft !== bDraft) return aDraft ? -1 : 1;
    return publishedAtMs(b) - publishedAtMs(a);
  });
}

export function MyProjectArticles({ projectSlugOrId }: Props) {
  const [articles, setArticles] = useState<ArticleListItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.articles
      .list(projectSlugOrId)
      .then((data) => {
        if (cancelled) return;
        setArticles(sortDraftsFirst(data));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load articles");
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlugOrId]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Drafts are listed first, then published articles, newest first.
        </p>
        <Link
          href={`/projects/${projectSlugOrId}/articles/new`}
          className="btn-primary text-sm py-2 px-3 inline-flex items-center gap-1.5"
        >
          <PlusIcon className="w-4 h-4" />
          New article
        </Link>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {articles === null ? (
        <div className="space-y-2">
          <div className="skeleton h-16 w-full rounded-lg" />
          <div className="skeleton h-16 w-full rounded-lg" />
        </div>
      ) : articles.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-6 text-center">
          No articles yet. Click <strong>New article</strong> to start one.
        </div>
      ) : (
        <ul className="space-y-2">
          {articles.map((article) => {
            const isDraft = article.state !== "published";
            return (
              <li
                key={article.id}
                className="rounded-lg border border-border bg-white hover:border-accent/50 transition-colors"
              >
                <Link
                  href={`/projects/${projectSlugOrId}/articles/edit/${article.id}`}
                  className="flex items-center gap-3 px-4 py-3"
                >
                  <ArticleListingImage
                    src={article.listing_image_url}
                    alt=""
                    crop={article.listing_crop}
                    className="w-20 flex-shrink-0 rounded"
                  />

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-base font-medium text-foreground truncate">
                        {article.title || "Untitled draft"}
                      </span>
                      {isDraft ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
                          Draft
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
                          Published
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                      <span className="font-semibold uppercase tracking-wide text-accent">
                        {article.channel.name}
                      </span>
                      {article.published_at && (
                        <time dateTime={article.published_at}>
                          {formatDate(article.published_at, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </time>
                      )}
                    </div>
                  </div>
                  <span className="text-sm text-accent">Edit →</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
