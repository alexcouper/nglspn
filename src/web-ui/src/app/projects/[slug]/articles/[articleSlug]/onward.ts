import type { CropRect } from "@/components/CroppedImage";
import type { Article, ArticleListItem, FeedEntry, Project } from "@/lib/api";
import { publishedNewestFirst } from "@/lib/article-listing";

/** How many cards sit beside the lead. */
const REST_SLOTS = 3;

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

export interface Onward {
  /** Always a true statement about what is below it — see buildOnward. */
  heading: string;
  moreHref: string;
  moreLabel: string;
  lead: OnwardCard;
  rest: OnwardCard[];
}

interface Input {
  project: Project;
  article: Article;
  /** The project's articles as the API returns them, drafts and all. */
  siblings: ArticleListItem[] | null;
  /** Only consulted when the project has published nothing else. */
  feed: FeedEntry[] | null;
}

/**
 * What the reader is handed when the article ends.
 *
 * Three cases, in order of how closely related the suggestions are. The
 * heading names whichever one applied, so it is never a promise the cards
 * below it do not keep:
 *
 *   1. the channel has other articles  → "More in <channel>"
 *   2. the project does, in other channels → "More from <project>"
 *   3. neither → "Elsewhere on Naglasúpan", from the site feed
 *
 * Deliberately not "Next in <channel>" when a newer article exists: the
 * reader cannot see which wording they would otherwise have got, so the
 * distinction buys nothing and costs a branch.
 *
 * Returns null when there is genuinely nothing to show, which is the one case
 * where the section should not render at all.
 */
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

  // Newest-first and with the current article removed, so the first entry is
  // the one after this in the channel — or, where this is the newest, the one
  // before it. Either way it is the nearest neighbour.
  const ordered = sameChannel.length ? [...sameChannel, ...elsewhere] : elsewhere;

  if (ordered.length) {
    const cards = ordered.map((a) => projectCard(a, projectSlug, project));
    return {
      heading: sameChannel.length
        ? `More in ${article.channel.name}`
        : `More from ${project.title}`,
      // There is no per-channel listing page, so this goes to the project's
      // articles tab — which is where all of them are, channel or not.
      moreHref: `/projects/${projectSlug}#articles`,
      moreLabel: `All ${others.length + 1} articles from ${project.title}`,
      lead: cards[0],
      rest: cards.slice(1, 1 + REST_SLOTS),
    };
  }

  const fromFeed = (feed ?? [])
    .filter((entry) => entry.article && entry.article.id !== article.id)
    .map(feedCard)
    .filter((card): card is OnwardCard => card !== null);

  if (!fromFeed.length) return null;

  return {
    heading: "Elsewhere on Naglasúpan",
    moreHref: "/latest",
    moreLabel: "Everything that's happened lately",
    lead: fromFeed[0],
    rest: fromFeed.slice(1, 1 + REST_SLOTS),
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
    // A channel named after its project reads as a stutter, the same way it
    // does on a feed row.
    flag: article.channel.name === project.title ? project.title : article.channel.name,
    title: article.title,
    summary: article.summary ?? "",
    imageUrl: article.listing_image_url ?? null,
    crop: article.listing_crop ?? null,
  };
}

function feedCard(entry: FeedEntry): OnwardCard | null {
  const article = entry.article;
  if (!article?.slug || !article.project_slug) return null;
  return {
    id: article.id,
    href: `/projects/${article.project_slug}/articles/${article.slug}`,
    // Off this project entirely, so the project is the useful label and the
    // channel is house plumbing.
    flag: article.project_title,
    title: article.title,
    summary: article.summary ?? "",
    imageUrl: article.listing_image_url ?? null,
    crop: article.listing_crop ?? null,
  };
}
