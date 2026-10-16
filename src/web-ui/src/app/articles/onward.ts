import type { CropRect } from "@/components/CroppedImage";
import type { Article, ArticleListItem, FeedEntry, UserArticle } from "@/lib/api";
import { publishedNewestFirst } from "@/lib/article-listing";
import {
  type Container,
  articleHref,
  containerArticlesHref,
  containerTitle,
} from "./container";

/** The lead plus the cards beside it. */
export const ONWARD_SLOTS = 4;

export interface OnwardCard {
  id: string;
  href: string;
  /** Small label above the headline: the channel, or the container when the card is from elsewhere. */
  flag: string;
  title: string;
  summary: string;
  imageUrl: string | null;
  crop: CropRect | null;
}

export type OnwardHeading =
  | { kind: "channel"; channel: string }
  | { kind: "project"; project: string }
  | { kind: "author"; author: string }
  | { kind: "elsewhere" };

export interface OnwardGroup {
  heading: OnwardHeading;
  cards: OnwardCard[];
}

export type OnwardMore =
  | { kind: "project"; href: string; count: number; project: string }
  | { kind: "author"; href: string; count: number; author: string }
  | { kind: "latest"; href: string };

export interface Onward {
  /** Never empty; its first card is the lead. */
  primary: OnwardGroup;
  /** Site-feed cards filling the slots a thin container leaves empty. */
  topUp: OnwardGroup | null;
  more: OnwardMore;
}

// What a sibling card needs. A project's list (`ArticleListItem`) carries
// visibility fields a profile's list (`UserArticle`) does not; both have this.
export type OnwardSibling = Pick<
  ArticleListItem,
  "id" | "slug" | "title" | "summary" | "published_at" | "channel" | "listing_image_url" | "listing_crop"
> &
  Partial<Pick<ArticleListItem, "state">> &
  Partial<Pick<UserArticle, "project">>;

interface Input {
  container: Container;
  article: Article;
  /** The container's other articles as the API returns them, drafts and all. */
  siblings: OnwardSibling[] | null;
  feed: FeedEntry[] | null;
}

export function buildOnward({ container, article, siblings, feed }: Input): Onward | null {
  const others = publishedSiblings(container, siblings ?? []).filter(
    (a) => a.id !== article.id,
  );

  // Channels only mean something on a project; an author's articles are one
  // list, so every sibling is "same channel" and the heading names the author.
  const channelId = container.kind === "project" ? (article.channel?.id ?? null) : null;
  const sameChannel = others.filter((a) => channelId === null || a.channel?.id === channelId);
  const elsewhere = others.filter((a) => channelId !== null && a.channel?.id !== channelId);
  const fromContainer = [...sameChannel, ...elsewhere]
    .slice(0, ONWARD_SLOTS)
    .map((a) => containerCard(a, container));

  const fromFeed = feedCards(feed ?? [], container, article).slice(
    0,
    ONWARD_SLOTS - fromContainer.length,
  );
  const elsewhereGroup: OnwardGroup | null = fromFeed.length
    ? { heading: { kind: "elsewhere" }, cards: fromFeed }
    : null;

  if (!fromContainer.length) {
    if (!elsewhereGroup) return null;
    return {
      primary: elsewhereGroup,
      topUp: null,
      more: { kind: "latest", href: "/latest" },
    };
  }

  return {
    primary: {
      heading: primaryHeading(container, article, fromContainer.length <= sameChannel.length),
      cards: fromContainer,
    },
    topUp: elsewhereGroup,
    more: moreFrom(container, others.length + 1),
  };
}

function primaryHeading(
  container: Container,
  article: Article,
  allInChannel: boolean,
): OnwardHeading {
  if (container.kind === "author") {
    return { kind: "author", author: containerTitle(container) };
  }
  if (allInChannel && article.channel) {
    return { kind: "channel", channel: article.channel.name };
  }
  return { kind: "project", project: container.project.title };
}

function moreFrom(container: Container, count: number): OnwardMore {
  const href = containerArticlesHref(container);
  return container.kind === "project"
    ? { kind: "project", href, count, project: container.project.title }
    : { kind: "author", href, count, author: containerTitle(container) };
}

// Published only, newest first, and — on a profile — only the author-owned
// ones: an author's project articles belong to their projects' pages.
function publishedSiblings(container: Container, siblings: OnwardSibling[]): OnwardSibling[] {
  const own =
    container.kind === "author" ? siblings.filter((a) => a.project === null) : siblings;
  return publishedNewestFirst(own);
}

function containerCard(article: OnwardSibling, container: Container): OnwardCard {
  const title = containerTitle(container);
  return {
    id: article.id,
    href: articleHref(container, article.slug ?? ""),
    // An author's channel is a placeholder nobody chose, and a channel named
    // after its project would repeat the heading; both read as the container.
    flag:
      container.kind === "project" && article.channel && article.channel.name !== title
        ? article.channel.name
        : title,
    title: article.title,
    summary: article.summary ?? "",
    imageUrl: article.listing_image_url ?? null,
    crop: article.listing_crop ?? null,
  };
}

function feedCards(feed: FeedEntry[], container: Container, current: Article): OnwardCard[] {
  const seen = new Set<string>();
  const cards: OnwardCard[] = [];
  for (const entry of feed) {
    const article = entry.article;
    if (!article?.slug) continue;
    if (article.id === current.id || isFromContainer(article, container)) continue;
    const href = feedArticleHref(article);
    if (!href || seen.has(article.id)) continue;
    seen.add(article.id);
    cards.push({
      id: article.id,
      href,
      flag: article.project_title ?? article.author_name ?? "",
      title: article.title,
      summary: article.summary ?? "",
      imageUrl: article.listing_image_url ?? null,
      crop: article.listing_crop ?? null,
    });
  }
  return cards;
}

type FeedArticleRef = NonNullable<FeedEntry["article"]>;

function isFromContainer(article: FeedArticleRef, container: Container): boolean {
  if (container.kind === "project") {
    return article.project_slug !== null && article.project_slug === container.project.slug;
  }
  return article.project_slug === null && article.author_id === container.author.id;
}

/** The public URL of a feed article: under its project, or under its author. */
export function feedArticleHref(article: FeedArticleRef): string | null {
  if (!article.slug) return null;
  if (article.project_slug) return `/projects/${article.project_slug}/articles/${article.slug}`;
  if (article.author_id) return `/users/${article.author_id}/articles/${article.slug}`;
  return null;
}
