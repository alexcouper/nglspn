import { ArticleAuthoringRoute } from "../../ArticleAuthoringRoute";

interface PageProps {
  params: Promise<{ slug: string; articleId: string }>;
}

// No server-side project fetch — see the sibling /new route and
// ArticleAuthoringRoute for why.
export default async function EditArticlePage({ params }: PageProps) {
  const { slug, articleId } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringRoute projectRef={slug} articleId={articleId} />
    </main>
  );
}
