import { ArticleAuthoringPage } from "../ArticleAuthoringPage";
import { getProjectOr404 } from "@/lib/api/server";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function NewArticlePage({ params }: PageProps) {
  const { slug } = await params;
  const project = await getProjectOr404(slug);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringPage project={project} />
    </main>
  );
}
