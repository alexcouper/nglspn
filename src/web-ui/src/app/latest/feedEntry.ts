import type { FeedEntry } from "@/lib/api";

type ArticleRef = NonNullable<FeedEntry["article"]>;
type ListingCrop = ArticleRef["listing_crop"];

// The API sends kinds and refs, never display copy. The wording lives here,
// with the rest of the UI's strings.
const KIND_FLAGS: Record<string, string> = {
  article_published: "Update",
  project_published: "New project",
  project_tipoff: "Tipoff",
  competition_opened: "Competition",
  competition_closed: "Competition closed",
  competition_winner: "Competition winner",
  discussion_promoted: "Discussion",
};

export interface RenderedEntry {
  id: string;
  /** Small label above the headline. */
  flag: string;
  headline: string;
  /** Standfirst or one-line context; empty when there is nothing worth saying. */
  summary: string;
  /** Where the row goes when followed. Null when the subject has no page. */
  href: string | null;
  /** Secondary line: project, category, competition. */
  meta: string;
  imageUrl: string | null;
  crop: ListingCrop;
  /** Project icons are square; article listing images are 16:9. */
  imageShape: "square" | "listing";
  occurredAt: string;
  /** Article-led rows get the richer treatment; bare events stay compact. */
  hasArticle: boolean;
}

/**
 * Flatten one feed entry into what a row renders.
 *
 * The three states of the design collapse here: an entry that carries an
 * article takes its headline from the article, and its flag from whatever
 * event it superseded — so a winner write-up still reads as a competition
 * winner. Everything else is a bare event.
 */
export function renderEntry(entry: FeedEntry): RenderedEntry {
  const article = entry.article;
  const supersededKind = entry.supersedes?.kind;

  if (article) {
    return {
      id: entry.id,
      // An article about an event keeps the event's flag; a standalone one is
      // labelled by its channel.
      flag: supersededKind
        ? (KIND_FLAGS[supersededKind] ?? article.channel_name)
        : article.channel_name,
      headline: article.title,
      summary: article.summary ?? "",
      href: articleHref(entry),
      meta: [article.project_title, article.channel_name]
        .filter(Boolean)
        .join(" · "),
      imageUrl: article.listing_image_url ?? null,
      crop: article.listing_crop ?? null,
      imageShape: "listing",
      occurredAt: entry.occurred_at,
      hasArticle: true,
    };
  }

  return {
    id: entry.id,
    flag: KIND_FLAGS[entry.kind] ?? "Update",
    headline: bareHeadline(entry),
    summary: "",
    href: bareHref(entry),
    meta: bareMeta(entry),
    // A bare project row shows the project's icon — the same image and size
    // Discover's cards use, so a project looks the same in both places.
    imageUrl: entry.project?.icon_url ?? null,
    crop: null,
    imageShape: "square",
    occurredAt: entry.occurred_at,
    hasArticle: false,
  };
}

function articleHref(entry: FeedEntry): string | null {
  const article = entry.article;
  if (!article?.slug || !article.project_slug) return null;
  return `/projects/${article.project_slug}/articles/${article.slug}`;
}

function bareHeadline(entry: FeedEntry): string {
  if (entry.competition) {
    return entry.kind === "competition_winner" && entry.competition.winner_slug
      ? `${entry.competition.name} has a winner`
      : entry.competition.name;
  }
  if (entry.project) return entry.project.title;
  if (entry.discussion) return entry.discussion.excerpt;
  return "";
}

function bareHref(entry: FeedEntry): string | null {
  if (entry.competition) return `/competitions/${entry.competition.id}`;
  if (entry.project?.slug) return `/projects/${entry.project.slug}`;
  if (entry.discussion?.project_slug) {
    return `/projects/${entry.discussion.project_slug}/discussions`;
  }
  return null;
}

function bareMeta(entry: FeedEntry): string {
  if (entry.project) return entry.project.category_name ?? "";
  if (entry.discussion) return entry.discussion.project_title;
  return "";
}

/**
 * Group entries under week headers — the only grouping the feed applies.
 *
 * Weeks start on Monday. Entries arrive newest-first and stay in that order
 * inside each group; grouping never reorders anything.
 */
export function groupByWeek(
  entries: FeedEntry[],
): { key: string; startsAt: Date; entries: FeedEntry[] }[] {
  const groups = new Map<string, { startsAt: Date; entries: FeedEntry[] }>();

  for (const entry of entries) {
    const startsAt = startOfWeek(new Date(entry.occurred_at));
    const key = startsAt.toISOString();
    const group = groups.get(key);
    if (group) {
      group.entries.push(entry);
    } else {
      groups.set(key, { startsAt, entries: [entry] });
    }
  }

  return [...groups.entries()].map(([key, group]) => ({ key, ...group }));
}

function startOfWeek(date: Date): Date {
  const result = new Date(date);
  // getDay() is 0 on Sunday, which belongs to the week that began six days ago.
  const dayOffset = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - dayOffset);
  result.setHours(0, 0, 0, 0);
  return result;
}

export function weekLabel(startsAt: Date, now: Date = new Date()): string {
  const thisWeek = startOfWeek(now).getTime();
  const weeksAgo = Math.round((thisWeek - startsAt.getTime()) / 604800000);
  if (weeksAgo <= 0) return "This week";
  if (weeksAgo === 1) return "Last week";
  return startsAt.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: startsAt.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}
