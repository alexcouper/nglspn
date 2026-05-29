import { notFound } from "next/navigation";
import { ArticleAuthoringPage } from "../../ArticleAuthoringPage";
import { fetchProject, ApiNotFoundError } from "@/lib/api/server";

interface PageProps {
  params: Promise<{ slug: string; articleId: string }>;
}

export default async function EditArticlePage({ params }: PageProps) {
  const { slug, articleId } = await params;

  let project;
  try {
    project = await fetchProject(slug);
  } catch (err) {
    if (err instanceof ApiNotFoundError) notFound();
    throw err;
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringPage
        project={project}
        mode="edit"
        articleId={articleId}
      />
    </main>
  );
}
