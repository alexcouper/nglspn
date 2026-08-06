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

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug, articleSlug } = await params;
  try {
    const article = await fetchArticleBySlug(slug, articleSlug);
    return {
      title: `${article.title} — ${article.project.title}`,
      description: article.body.slice(0, 160).trim(),
      openGraph: {
        type: "article",
        title: article.title,
        description: article.body.slice(0, 160).trim(),
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
