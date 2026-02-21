import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ReadOnlyProjectDetail } from "@/app/my-projects/[id]/ReadOnlyProjectDetail";
import { fetchProject, getAllProjectIds } from "@/lib/api/server";
export const revalidate = 3600;

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  const ids = await getAllProjectIds();
  return ids.map((id) => ({ id }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  try {
    const project = await fetchProject(id);
    const mainImage = project.images?.find((img) => img.is_main) || project.images?.[0];
    return {
      title: project.title,
      description: project.tagline || undefined,
      openGraph: {
        title: project.title,
        description: project.tagline || undefined,
        ...(mainImage && { images: [{ url: mainImage.url }] }),
      },
    };
  } catch {
    return {};
  }
}

export default async function ProjectPage({ params }: PageProps) {
  const { id } = await params;

  let project;
  try {
    project = await fetchProject(id);
  } catch {
    notFound();
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <ReadOnlyProjectDetail project={project} showStatus={false} />
        </div>
      </section>
    </main>
  );
}
