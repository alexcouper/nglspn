import { ArticleAuthoringRoute } from "../../ArticleAuthoringRoute";

interface PageProps {
  params: Promise<{ slug: string; articleId: string }>;
}

// No server-side project fetch: it would be anonymous, and the backend 404s an
// unapproved project for an anonymous caller. See ArticleAuthoringRoute.
export default async function EditArticlePage({ params }: PageProps) {
  const { slug, articleId } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringRoute projectRef={slug} articleId={articleId} />
    </main>
  );
}
