import type { ArticleListItem, OwnArticle } from "@/lib/api";

// The fields the listing rules read. Structural so a project's list
// (`ArticleListItem`), the owner's (`OwnArticle`) and a profile's public one
// (`UserArticle`, which carries no state: everything in it is published) can
// all go through them.
export interface ListedArticle {
  slug: string | null;
  published_at: string | null;
  state?: string;
}

// Published only, newest first. An authenticated author gets their own drafts
// back from the same endpoint, and an article without a slug has no URL.
export function publishedNewestFirst<T extends ListedArticle>(articles: T[]): T[] {
  return articles
    .filter((a) => (a.state ?? "published") === "published" && a.slug)
    .sort((x, y) => publishedTime(y) - publishedTime(x));
}

function publishedTime(article: ListedArticle): number {
  return article.published_at ? new Date(article.published_at).getTime() : 0;
}

// Drafts first, then published articles newest first — the order an author's
// own list reads in, on my-projects and on their profile alike.
export function sortDraftsFirst<T extends ListedArticle>(articles: T[]): T[] {
  return [...articles].sort((a, b) => {
    const aDraft = a.state !== "published";
    const bDraft = b.state !== "published";
    if (aDraft !== bDraft) return aDraft ? -1 : 1;
    return publishedTime(b) - publishedTime(a);
  });
}

export const BADGE_TONES = {
  draft: "bg-amber-50 border-amber-200 text-amber-800",
  live: "bg-emerald-50 border-emerald-200 text-emerald-800",
  held: "bg-slate-100 border-slate-300 text-slate-700",
} as const;

// A published article the site isn't showing gets its own badge rather than the
// green one. The author's own lists are the only place they can find that out,
// so "Published" on its own would be a lie — the article exists, and nobody
// else can see it.
export type BadgeKey = "draft" | "published" | "pendingReview" | "notShown";

type BadgedArticle = Pick<
  ArticleListItem | OwnArticle,
  "state" | "is_globally_visible" | "global_visibility"
>;

export function articleBadge(article: BadgedArticle): {
  key: BadgeKey;
  tone: string;
} {
  if (article.state !== "published") {
    return { key: "draft", tone: BADGE_TONES.draft };
  }
  if (article.is_globally_visible) {
    return { key: "published", tone: BADGE_TONES.live };
  }
  return {
    key: article.global_visibility === "pending" ? "pendingReview" : "notShown",
    tone: BADGE_TONES.held,
  };
}
