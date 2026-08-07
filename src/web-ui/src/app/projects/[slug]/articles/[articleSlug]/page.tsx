import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArticleRenderContent } from "./ArticleRenderContent";
import {
  fetchArticleBySlug,
  getProjectOr404,
  ApiNotFoundError,
} from "@/lib/api/server";

interface PageProps {
  params: Promise<{ slug: string; articleSlug: string }>;
}

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
}: PageProps): Promise<Metadata> {
  const { slug, articleSlug } = await params;
  try {
    const article = await fetchArticleBySlug(slug, articleSlug);
    // Never the body: that is markdown, and `## headings`, `**bold**` and
    // `[links](url)` would go verbatim into the meta tags. `summary` is the
    // authored standfirst; `summary_display` is the server's plain-text
    // excerpt of the body, which is what this wanted in the first place.
    const description = truncate(article.summary || article.summary_display);
    return {
      title: `${article.title} — ${article.project.title}`,
      description,
      openGraph: {
        type: "article",
        title: article.title,
        description,
        // The uncropped original. The author's 16:9 framing is applied in CSS
        // at render time (see CroppedImage), so there is no cropped file to
        // point a scraper at — Facebook and Slack show the whole image.
        ...(article.listing_image_url && {
          images: [{ url: article.listing_image_url, alt: article.title }],
        }),
      },
    };
  } catch {
    return {};
  }
}

export default async function ArticleRenderPage({ params }: PageProps) {
  const { slug, articleSlug } = await params;

  // `getProjectOr404` handles the project 404; the article fetch needs its
  // own try because draft articles return 404 for unauthenticated server
  // fetches (the client-side path in ArticleRenderContent rehydrates drafts
  // for the author / full_edit contributors).
  const [project, article] = await Promise.all([
    getProjectOr404(slug),
    fetchArticleBySlug(slug, articleSlug).catch((err) => {
      if (err instanceof ApiNotFoundError) notFound();
      throw err;
    }),
  ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleRenderContent project={project} article={article} />
    </main>
  );
}
