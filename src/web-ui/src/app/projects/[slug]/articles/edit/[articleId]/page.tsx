import { ArticleAuthoringPage } from "../../ArticleAuthoringPage";
import { getProjectOr404 } from "@/lib/api/server";

interface PageProps {
  params: Promise<{ slug: string; articleId: string }>;
}

export default async function EditArticlePage({ params }: PageProps) {
  const { slug, articleId } = await params;
  const project = await getProjectOr404(slug);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringPage project={project} articleId={articleId} />
    </main>
  );
}
