"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowPathIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";
import { ArticleListingImage } from "@/components/ArticleListingImage";
import type { ArticleListItem, Channel } from "@/lib/api";
import { api } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { articleBadge, sortDraftsFirst } from "@/lib/article-listing";
import { formatDate } from "@/lib/utils";

interface Props {
  projectSlugOrId: string;
}

export function MyProjectArticles({ projectSlugOrId }: Props) {
  const router = useRouter();
  const t = useTranslations("my-projects.articles");
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
        setError(err instanceof Error ? err.message : t("errors.loadFailed"));
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
  }, [projectSlugOrId, t]);

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
      router.push(`/articles/edit/${created.id}`);
    } catch (err) {
      setError(describeApiError(err, t("errors.createFailed")));
      setIsCreating(false);
    }
  }, [channels, isCreating, projectSlugOrId, router, t]);

  const canCreate = !!channels?.length && !isCreating;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t("ordering")}
        </p>
        <button
          type="button"
          onClick={handleNewArticle}
          disabled={!canCreate}
          title={
            channels?.length === 0
              ? t("noChannel")
              : undefined
          }
          className="btn-primary text-sm py-2 px-3 inline-flex items-center gap-1.5 disabled:opacity-60"
        >
          {isCreating ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            <PlusIcon className="w-4 h-4" />
          )}
          {t("newArticle")}
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
          {t.rich("empty", { strong: (chunks) => <strong>{chunks}</strong> })}
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
                  href={`/articles/edit/${article.id}`}
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
                        {article.title || t("untitledDraft")}
                      </span>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${badge.tone}`}
                      >
                        {t(`badge.${badge.key}`)}
                      </span>
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                      <span className="font-semibold uppercase tracking-wide text-accent">
                        {article.channel?.name}
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
                  <span className="text-sm text-accent">{t("edit")}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
