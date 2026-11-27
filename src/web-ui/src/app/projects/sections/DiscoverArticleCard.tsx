"use client";

import { frontPageArticleHref } from "@/app/articles/onward";
import { withOrigin } from "@/app/articles/origin";
import { ArticleCard } from "@/components/ArticleCard";
import type { FrontPageArticle } from "@/lib/api";

interface Props {
  article: FrontPageArticle;
  variant: "lead" | "grid";
}

// A front-page article, set unboxed on the page with a hairline under it: flagged with its project, or its author for
// an author-owned article, and linked so the back control returns to Discover.
export function DiscoverArticleCard({ article, variant }: Props) {
  const isAuthorOwned = article.project_slug === null;
  const href = frontPageArticleHref(article);

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
      frame="ruled"
    />
  );
}
