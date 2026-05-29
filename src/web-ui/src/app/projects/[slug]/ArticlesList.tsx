"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { api } from "@/lib/api";

interface Props {
  projectSlug: string;
}

export function ArticlesList({ projectSlug }: Props) {
  const [articles, setArticles] = useState<ArticleListItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.articles
      .list(projectSlug)
      .then((data) => {
        if (cancelled) return;
        setArticles(
          data
            .filter((a) => a.state === "published" && a.slug)
            .sort((x, y) => {
              const xt = x.published_at
                ? new Date(x.published_at).getTime()
                : 0;
              const yt = y.published_at
                ? new Date(y.published_at).getTime()
                : 0;
              return yt - xt;
            }),
        );
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load articles");
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlug]);

  if (error) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error}
      </p>
    );
  }
  if (articles === null) {
    return (
      <div className="space-y-3">
        <div className="skeleton h-24 w-full rounded-lg" />
        <div className="skeleton h-24 w-full rounded-lg" />
      </div>
    );
  }
  if (articles.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No articles yet.</p>
    );
  }

  return (
    <ul className="space-y-3">
      {articles.map((article) => (
        <li
          key={article.id}
          className="rounded-lg border border-border bg-white hover:border-accent/50 transition-colors"
        >
          <Link
            href={`/projects/${projectSlug}/articles/${article.slug}`}
            className="flex gap-4 p-4"
          >
            {article.hero_image_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={article.hero_image_url}
                alt=""
                className="w-24 h-24 rounded-md object-cover flex-shrink-0 bg-muted"
              />
            ) : (
              <div className="w-24 h-24 rounded-md bg-muted flex-shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold uppercase tracking-wide text-accent mb-1">
                {article.channel.name}
              </div>
              <div className="text-base font-medium text-foreground line-clamp-2">
                {article.title}
              </div>
              {article.published_at && (
                <div className="mt-1 text-xs text-muted-foreground">
                  {new Date(article.published_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </div>
              )}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
