"use client";

import { useEffect, useState } from "react";
import { ArticleCard } from "@/components/ArticleCard";
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
      <div className="space-y-5">
        <div className="skeleton aspect-[16/9] w-full rounded-lg" />
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="skeleton aspect-[16/9] w-full rounded-lg" />
          <div className="skeleton aspect-[16/9] w-full rounded-lg" />
        </div>
      </div>
    );
  }
  if (articles.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No articles yet.</p>
    );
  }

  // The empty guard above means `lead` is always defined here.
  const [lead, ...rest] = articles;

  return (
    <div className="space-y-5">
      <ArticleCard
        article={lead}
        href={`/projects/${projectSlug}/articles/${lead.slug}`}
        variant="lead"
      />
      {rest.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2">
          {rest.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              href={`/projects/${projectSlug}/articles/${article.slug}`}
              variant="grid"
            />
          ))}
        </div>
      )}
    </div>
  );
}
