import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArticleRenderContent } from "./ArticleRenderContent";
import { socialCard } from "@/lib/social-card";
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

export default async function ArticleRenderPage({ params }: PageProps) {
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
