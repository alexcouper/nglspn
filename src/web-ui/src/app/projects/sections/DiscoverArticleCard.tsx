"use client";

import { withOrigin } from "@/app/articles/origin";
import { ArticleCard } from "@/components/ArticleCard";
import type { FrontPageArticle } from "@/lib/api";

interface Props {
  article: FrontPageArticle;
  variant: "lead" | "grid" | "overlay";
}

// A front-page article as a card: flagged with its project, or its author for
// an author-owned article, and linked so the back control returns to Discover.
export function DiscoverArticleCard({ article, variant }: Props) {
  const isAuthorOwned = article.project_slug === null;
  const href = articleHref(article);

  return (
    <ArticleCard
      article={{
        ...article,
        channel: article.channel_name ? { name: article.channel_name } : null,
      }}
      flag={article.project_title ?? article.author_name ?? undefined}
      showChannel={!isAuthorOwned}
      href={href ? withOrigin(href, "discover") : undefined}
      variant={variant}
    />
  );
}

function articleHref(article: FrontPageArticle): string | null {
  if (!article.slug) return null;
  if (article.project_slug) return `/projects/${article.project_slug}/articles/${article.slug}`;
  if (article.author_id) return `/users/${article.author_id}/articles/${article.slug}`;
  return null;
}
