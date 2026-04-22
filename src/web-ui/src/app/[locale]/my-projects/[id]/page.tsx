import { ProjectDetail } from "./ProjectDetail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MyProjectPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectDetail projectId={id} />
    </main>
  );
}
