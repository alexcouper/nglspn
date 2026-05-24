import { redirect } from "next/navigation";
import { fetchProject, ApiNotFoundError } from "@/lib/api/server";

interface PageProps {
  params: Promise<{ competitionId: string; projectId: string }>;
}

export default async function MyReviewsProjectRedirect({ params }: PageProps) {
  const { projectId } = await params;
  try {
    const project = await fetchProject(projectId);
    redirect(`/projects/${project.slug ?? project.id}`);
  } catch (err) {
    if (err instanceof ApiNotFoundError) {
      redirect("/competitions");
    }
    throw err;
  }
}
