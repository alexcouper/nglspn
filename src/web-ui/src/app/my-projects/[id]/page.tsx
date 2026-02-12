import { ProjectDetail } from "./ProjectDetail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MyProjectPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Edit Project
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Update your submission
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <ProjectDetail projectId={id} />
        </div>
      </section>
    </main>
  );
}
