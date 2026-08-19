"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowPathIcon, PlusIcon } from "@heroicons/react/24/outline";
import { ArticleListingImage } from "@/components/ArticleListingImage";
import type { ArticleListItem, Channel } from "@/lib/api";
import { api } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
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

const BADGE_TONES = {
  draft: "bg-amber-50 border-amber-200 text-amber-800",
  live: "bg-emerald-50 border-emerald-200 text-emerald-800",
  held: "bg-slate-100 border-slate-300 text-slate-700",
} as const;

// A published article the site isn't showing gets its own badge rather than the
// green one. This table is the only place its author can find that out, so
// "Published" on its own would be a lie — the article exists, and nobody else
// can see it.
function articleBadge(article: ArticleListItem): {
  label: string;
  tone: string;
} {
  if (article.state !== "published") {
    return { label: "Draft", tone: BADGE_TONES.draft };
  }
  if (article.is_globally_visible) {
    return { label: "Published", tone: BADGE_TONES.live };
  }
  return {
    label:
      article.global_visibility === "pending" ? "Pending review" : "Not shown",
    tone: BADGE_TONES.held,
  };
}

export function MyProjectArticles({ projectSlugOrId }: Props) {
  const router = useRouter();
  const [articles, setArticles] = useState<ArticleListItem[] | null>(null);
  // Null until the lookup settles. Only the New article button reads it, so a
  // failure here disables that button rather than taking the list down with it.
  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [isCreating, setIsCreating] = useState(false);
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
    // Fetched here, next to the list, because this is where a draft is created:
    // `ArticleCreate.channel_id` is required, so the button cannot act until a
    // channel is known. Settled separately from the list so neither waits on
    // the other.
    api.channels
      .list(projectSlugOrId)
      .then((data) => {
        if (cancelled) return;
        setChannels(data);
      })
      .catch(() => {
        if (cancelled) return;
        setChannels([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlugOrId]);

  // The draft is created here rather than on a /new route: an article has to
  // exist before the editor opens (images are uploaded against it), and a route
  // that creates on mount then rewrites the URL makes the author sit through
  // two page loads. Creating on the click costs one navigation, onto a page
  // that already has its article.
  const handleNewArticle = useCallback(async () => {
    const channelId = channels?.[0]?.id;
    if (!channelId || isCreating) return;
    setIsCreating(true);
    setError("");
    try {
      const created = await api.articles.create(projectSlugOrId, {
        channel_id: channelId,
        title: "",
        body: "",
      });
      router.push(`/projects/${projectSlugOrId}/articles/edit/${created.id}`);
    } catch (err) {
      setError(describeApiError(err, "Couldn't start a new article."));
      setIsCreating(false);
    }
  }, [channels, isCreating, projectSlugOrId, router]);

  const canCreate = !!channels?.length && !isCreating;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Drafts are listed first, then published articles, newest first.
        </p>
        <button
          type="button"
          onClick={handleNewArticle}
          disabled={!canCreate}
          title={
            channels?.length === 0
              ? "This project has no channel to publish an article into."
              : undefined
          }
          className="btn-primary text-sm py-2 px-3 inline-flex items-center gap-1.5 disabled:opacity-60"
        >
          {isCreating ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            <PlusIcon className="w-4 h-4" />
          )}
          New article
        </button>
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
            const badge = articleBadge(article);
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
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${badge.tone}`}
                      >
                        {badge.label}
                      </span>
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
