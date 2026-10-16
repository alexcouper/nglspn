import { ArticleAuthoringRoute } from "../../ArticleAuthoringRoute";

interface PageProps {
  params: Promise<{ articleId: string }>;
}

// One editor route for both kinds of article. No server-side fetch: it would
// be anonymous, and the backend 404s an article for anyone but its editors.
// See ArticleAuthoringRoute.
export default async function EditArticlePage({ params }: PageProps) {
  const { articleId } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringRoute articleId={articleId} />
    </main>
  );
}
