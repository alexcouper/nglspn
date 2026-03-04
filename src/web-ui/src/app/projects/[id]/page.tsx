import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ProjectDetailContent } from "./ProjectDetailContent";
import { fetchProject, getAllProjectIds, ApiNotFoundError } from "@/lib/api/server";
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
    const title = project.tagline
      ? `${project.title} — ${project.tagline}`
      : project.title;
    const description = project.description
      ? project.description.length > 100
        ? project.description.slice(0, 100).replace(/\s+\S*$/, "") + "…"
        : project.description
      : undefined;
    return {
      title,
      description: description,
      openGraph: {
        type: "website",
        siteName: "naglasúpan",
        url: `https://naglasupan.is/projects/${id}`,
        title,
        description: description,
        ...(mainImage && {
          images: [
            {
              url: mainImage.url,
              ...(mainImage.width && { width: mainImage.width }),
              ...(mainImage.height && { height: mainImage.height }),
              alt: project.title,
            },
          ],
        }),
      },
      twitter: {
        card: "summary_large_image",
        title,
        description: description,
        ...(mainImage && { images: [mainImage.url] }),
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
  } catch (err) {
    if (err instanceof ApiNotFoundError) notFound();
    throw err;
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectDetailContent project={project} projectId={id} />
    </main>
  );
}
