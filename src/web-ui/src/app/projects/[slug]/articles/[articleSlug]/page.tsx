import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ArticleRenderContent } from "./ArticleRenderContent";
import { buildOnward, ONWARD_SLOTS } from "./onward";
import { ORIGIN_PARAM, resolveOrigin } from "./origin";
import { socialCard } from "@/lib/social-card";
import {
  fetchArticleBySlug,
  fetchFeedPage,
  fetchProjectArticles,
  getProjectOr404,
  ApiNotFoundError,
} from "@/lib/api/server";
import { publishedNewestFirst } from "@/lib/article-listing";

interface PageProps {
  params: Promise<{ slug: string; articleSlug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

type MetadataProps = Pick<PageProps, "params">;

// What search results and social cards have room for.
const DESCRIPTION_MAX = 160;

// Trimmed at a word boundary, not mid-word.
function truncate(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= DESCRIPTION_MAX) return trimmed;
  return trimmed.slice(0, DESCRIPTION_MAX).replace(/\s+\S*$/, "") + "…";
}

export async function generateMetadata({
  params,
}: MetadataProps): Promise<Metadata> {
  const { slug, articleSlug } = await params;
  try {
    const [t, article] = await Promise.all([
      getTranslations("articles.page"),
      fetchArticleBySlug(slug, articleSlug),
    ]);
    // Never the body: that is markdown, and `## headings`, `**bold**` and
    // `[links](url)` would go verbatim into the meta tags. `summary` is the
    // authored standfirst; `summary_display` is the server's plain-text
    // excerpt of the body, which is what this wanted in the first place.
    const description = truncate(article.summary || article.summary_display);
    return {
      title: t("metaTitle", {
        articleTitle: article.title,
        projectTitle: article.project.title,
      }),
      description,
      // The uncropped original. The author's 16:9 framing is applied in CSS at
      // render time (see CroppedImage), so there is no cropped file to point a
      // scraper at — Facebook and Slack show the whole image.
      ...socialCard({
        type: "article",
        title: article.title,
        description,
        imageUrl: article.listing_image_url,
      }),
    };
  } catch {
    return {};
  }
}

export default async function ArticleRenderPage({
  params,
  searchParams,
}: PageProps) {
  const { slug, articleSlug } = await params;

  // `getProjectOr404` handles the project 404; the article fetch needs its own
  // catch to map a missing article onto the same 404.
  //
  // Only published articles resolve here, and nothing rehydrates a draft
  // afterwards. `serverFetch` sends no credentials — auth is a bearer token in
  // localStorage, so no server component can authenticate — so the backend
  // always sees an anonymous user and 404s on a draft. A draft has no slug to
  // be addressed by anyway: `publish_article` assigns one, and there is no
  // unpublish path. Previewing a draft needs a client-side route; see
  // FOLLOW_UPS.md item 7.
  const [project, article, siblings, query] = await Promise.all([
    getProjectOr404(slug),
    fetchArticleBySlug(slug, articleSlug).catch((err) => {
      if (err instanceof ApiNotFoundError) notFound();
      throw err;
    }),
    fetchProjectArticles(slug).catch(() => null),
    searchParams,
  ]);

  const published = publishedNewestFirst(siblings ?? []);
  const others = published.filter((a) => a.id !== article.id).length;
  const feed =
    others >= ONWARD_SLOTS
      ? null
      : await fetchFeedPage()
          .then((page) => page.entries)
          .catch(() => null);

  return (
    <main className="min-h-screen bg-white pt-14">
      <ArticleRenderContent
        project={project}
        article={article}
        origin={resolveOrigin(query[ORIGIN_PARAM], project)}
        onward={buildOnward({ project, article, siblings, feed })}
        articleCount={published.length}
        channelCount={new Set(published.map((a) => a.channel.id)).size}
      />
    </main>
  );
}
