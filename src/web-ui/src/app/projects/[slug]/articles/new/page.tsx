import { ArticleAuthoringRoute } from "../ArticleAuthoringRoute";

interface PageProps {
  params: Promise<{ slug: string }>;
}

// No server-side project fetch: it would be anonymous, and the backend 404s an
// unapproved project for an anonymous caller. See ArticleAuthoringRoute.
export default async function NewArticlePage({ params }: PageProps) {
  const { slug } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ArticleAuthoringRoute projectRef={slug} />
    </main>
  );
}
