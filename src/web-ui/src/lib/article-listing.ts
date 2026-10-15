import type { ArticleListItem } from "@/lib/api";

// Published only, newest first. An authenticated author gets their own drafts
// back from the same endpoint, and an article without a slug has no URL.
export function publishedNewestFirst(
  articles: ArticleListItem[],
): ArticleListItem[] {
  return articles
    .filter((a) => a.state === "published" && a.slug)
    .sort((x, y) => publishedTime(y) - publishedTime(x));
}

function publishedTime(article: ArticleListItem): number {
  return article.published_at ? new Date(article.published_at).getTime() : 0;
}
