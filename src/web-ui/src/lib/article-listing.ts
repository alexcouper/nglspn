import type { ArticleListItem } from "@/lib/api";

/**
 * The reader's view of a project's articles: published only, newest first.
 *
 * Applied to the server's response as well as the client's — an authenticated
 * author gets their own drafts back from the same endpoint, and an article
 * without a slug has no URL to be addressed by.
 *
 * Lives here rather than beside the listing that first needed it because the
 * article page's onward section applies the same rule, and importing it from a
 * component module would pull that component's whole tree into the article
 * route's bundle.
 */
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
