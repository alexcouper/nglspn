import { notFound, permanentRedirect } from "next/navigation";
import type { Metadata } from "next";
import { ProjectDetailContent } from "./ProjectDetailContent";
import { fetchProject, ApiNotFoundError } from "@/lib/api/server";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const project = await fetchProject(slug);
    const canonicalSlug = project.slug ?? slug;
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
        url: `https://naglasupan.is/projects/${canonicalSlug}`,
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
  const { slug } = await params;

  let project;
  try {
    project = await fetchProject(slug);
  } catch (err) {
    if (err instanceof ApiNotFoundError) notFound();
    throw err;
  }

  // Canonicalise: if the URL identifier isn't the project's current slug
  // (e.g. accessed by UUID), 301 to the slug URL.
  if (project.slug && project.slug !== slug) {
    permanentRedirect(`/projects/${project.slug}`);
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectDetailContent project={project} projectId={project.id} />
    </main>
  );
}
