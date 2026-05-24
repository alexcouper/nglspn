import { redirect } from "next/navigation";

interface PageProps {
  params: Promise<{ competitionId: string }>;
}

export default async function MyReviewsCompetitionRedirect({ params }: PageProps) {
  const { competitionId } = await params;
  redirect(`/competitions/${competitionId}`);
}
