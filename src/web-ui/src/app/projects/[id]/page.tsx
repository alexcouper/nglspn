import { PublicProjectDetail } from "./PublicProjectDetail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProjectPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <PublicProjectDetail projectId={id} />
        </div>
      </section>
    </main>
  );
}
