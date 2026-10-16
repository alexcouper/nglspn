import type { CropRect } from "@/components/CroppedImage";
import type { Article, ArticleListItem, FeedEntry, Project } from "@/lib/api";
import { publishedNewestFirst } from "@/lib/article-listing";

/** The lead plus the cards beside it. */
export const ONWARD_SLOTS = 4;

export interface OnwardCard {
  id: string;
  href: string;
  /** Small label above the headline: the channel, or the project when the card is from elsewhere. */
  flag: string;
  title: string;
  summary: string;
  imageUrl: string | null;
  crop: CropRect | null;
}

export type OnwardHeading =
  | { kind: "channel"; channel: string }
  | { kind: "project"; project: string }
  | { kind: "elsewhere" };

export interface OnwardGroup {
  heading: OnwardHeading;
  cards: OnwardCard[];
}

export type OnwardMore =
  | { kind: "project"; href: string; count: number; project: string }
  | { kind: "latest"; href: string };

export interface Onward {
  /** Never empty; its first card is the lead. */
  primary: OnwardGroup;
  /** Site-feed cards filling the slots a thin project leaves empty. */
  topUp: OnwardGroup | null;
  more: OnwardMore;
}

interface Input {
  project: Project;
  article: Article;
  /** The project's articles as the API returns them, drafts and all. */
  siblings: ArticleListItem[] | null;
  feed: FeedEntry[] | null;
}

export function buildOnward({
  project,
  article,
  siblings,
  feed,
}: Input): Onward | null {
  const projectSlug = project.slug ?? project.id;
  const others = publishedNewestFirst(siblings ?? []).filter(
    (a) => a.id !== article.id,
  );

  const sameChannel = others.filter((a) => a.channel.id === article.channel.id);
  const elsewhere = others.filter((a) => a.channel.id !== article.channel.id);
  const fromProject = [...sameChannel, ...elsewhere]
    .slice(0, ONWARD_SLOTS)
    .map((a) => projectCard(a, projectSlug, project));

  const fromFeed = feedCards(feed ?? [], project, article).slice(
    0,
    ONWARD_SLOTS - fromProject.length,
  );
  const elsewhereGroup: OnwardGroup | null = fromFeed.length
    ? { heading: { kind: "elsewhere" }, cards: fromFeed }
    : null;

  if (!fromProject.length) {
    if (!elsewhereGroup) return null;
    return {
      primary: elsewhereGroup,
      topUp: null,
      more: { kind: "latest", href: "/latest" },
    };
  }

  const allInChannel = fromProject.length <= sameChannel.length;
  return {
    primary: {
      heading: allInChannel
        ? { kind: "channel", channel: article.channel.name }
        : { kind: "project", project: project.title },
      cards: fromProject,
    },
    topUp: elsewhereGroup,
    more: {
      kind: "project",
      href: `/projects/${projectSlug}#articles`,
      count: others.length + 1,
      project: project.title,
    },
  };
}

function projectCard(
  article: ArticleListItem,
  projectSlug: string,
  project: Project,
): OnwardCard {
  return {
    id: article.id,
    href: `/projects/${projectSlug}/articles/${article.slug}`,
    flag: article.channel.name === project.title ? project.title : article.channel.name,
    title: article.title,
    summary: article.summary ?? "",
    imageUrl: article.listing_image_url ?? null,
    crop: article.listing_crop ?? null,
  };
}

function feedCards(
  feed: FeedEntry[],
  project: Project,
  current: Article,
): OnwardCard[] {
  const seen = new Set<string>();
  const cards: OnwardCard[] = [];
  for (const entry of feed) {
    const article = entry.article;
    if (!article?.slug || !article.project_slug) continue;
    if (article.id === current.id || article.project_slug === project.slug) continue;
    if (seen.has(article.id)) continue;
    seen.add(article.id);
    cards.push({
      id: article.id,
      href: `/projects/${article.project_slug}/articles/${article.slug}`,
      flag: article.project_title,
      title: article.title,
      summary: article.summary ?? "",
      imageUrl: article.listing_image_url ?? null,
      crop: article.listing_crop ?? null,
    });
  }
  return cards;
}
