import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ArticleRenderContent } from "./ArticleRenderContent";
import {
  fetchArticleBySlug,
  fetchProject,
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
        ...(article.hero_image_url && {
          images: [{ url: article.hero_image_url, alt: article.title }],
        }),
      },
    };
  } catch {
    return {};
  }
}

export default async function ArticleRenderPage({ params }: PageProps) {
  const { slug, articleSlug } = await params;

  let project, article;
  try {
    [project, article] = await Promise.all([
      fetchProject(slug),
      // Backend returns 404 for drafts to unauthenticated callers (server fetch
      // has no auth context). Authenticated callers (author / full_edit) hit
      // the client-side fetch path inside ArticleRenderContent for drafts.
      fetchArticleBySlug(slug, articleSlug),
    ]);
  } catch (err) {
    if (err instanceof ApiNotFoundError) notFound();
    throw err;
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleRenderContent project={project} article={article} />
    </main>
  );
}
