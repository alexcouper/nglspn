import { redirect } from "next/navigation";

interface PageProps {
  params: Promise<{ competitionId: string; projectId: string }>;
}

export default async function MyReviewsProjectRedirect({ params }: PageProps) {
  const { projectId } = await params;
  redirect(`/projects/${projectId}`);
}
