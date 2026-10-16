import { redirect } from "next/navigation";

interface PageProps {
  params: Promise<{ slug: string; articleId: string }>;
}

// The editor moved to /articles/edit/{id} when articles stopped needing a
// project; a browser tab holding the old address lands on the new one.
export default async function LegacyEditArticlePage({ params }: PageProps) {
  const { articleId } = await params;
  redirect(`/articles/edit/${articleId}`);
}
