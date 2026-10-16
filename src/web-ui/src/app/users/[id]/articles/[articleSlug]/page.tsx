import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ArticleRenderContent } from "@/app/articles/ArticleRenderContent";
import { authorContainer } from "@/app/articles/container";
import { buildOnward, ONWARD_SLOTS } from "@/app/articles/onward";
import { ORIGIN_PARAM, resolveOrigin } from "@/app/articles/origin";
import { socialCard } from "@/lib/social-card";
import {
  fetchAuthorArticleBySlug,
  fetchFeedPage,
  fetchUserArticles,
  getPublicProfileOr404,
  ApiNotFoundError,
} from "@/lib/api/server";
import { getAuthorName } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string; articleSlug: string }>;
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
  const { id, articleSlug } = await params;
  try {
    const [t, article] = await Promise.all([
      getTranslations("articles.page"),
      fetchAuthorArticleBySlug(id, articleSlug),
    ]);
    // Never the body: that is markdown. See the project form of this page.
    const description = truncate(article.summary || article.summary_display);
    return {
      title: t("metaTitleAuthor", {
        articleTitle: article.title,
        authorName: article.author ? getAuthorName(article.author) : "",
      }),
      description,
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

// The author-owned twin of /projects/[slug]/articles/[articleSlug]: the same
// render content, with the author where the project would be. Anonymous
// fetches, as there — a draft 404s for everyone here, and the author previews
// theirs through the editor.
export default async function AuthorArticleRenderPage({
  params,
  searchParams,
}: PageProps) {
  const { id, articleSlug } = await params;

  const [author, article, siblings, query] = await Promise.all([
    getPublicProfileOr404(id),
    fetchAuthorArticleBySlug(id, articleSlug).catch((err) => {
      if (err instanceof ApiNotFoundError) notFound();
      throw err;
    }),
    fetchUserArticles(id).catch(() => null),
    searchParams,
  ]);

  const own = (siblings ?? []).filter((a) => a.project === null);
  const others = own.filter((a) => a.id !== article.id).length;
  const feed =
    others >= ONWARD_SLOTS
      ? null
      : await fetchFeedPage()
          .then((page) => page.entries)
          .catch(() => null);

  const container = authorContainer(author);
  return (
    <main className="min-h-screen bg-white pt-14">
      <ArticleRenderContent
        container={container}
        article={article}
        origin={resolveOrigin(query[ORIGIN_PARAM], container)}
        onward={buildOnward({ container, article, siblings, feed })}
        articleCount={own.length}
        channelCount={1}
      />
    </main>
  );
}
