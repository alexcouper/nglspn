import { permanentRedirect } from "next/navigation";
import type { Metadata } from "next";
import { ProjectDetailContent } from "./ProjectDetailContent";
import { socialCard } from "@/lib/social-card";
import {
  fetchProject,
  fetchProjectArticles,
  getProjectOr404,
} from "@/lib/api/server";

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
      description,
      ...socialCard({
        title,
        description,
        url: `https://naglasupan.is/projects/${canonicalSlug}`,
        imageUrl: mainImage?.url,
        imageWidth: mainImage?.width ?? undefined,
        imageHeight: mainImage?.height ?? undefined,
      }),
    };
  } catch {
    return {};
  }
}

export default async function ProjectPage({ params }: PageProps) {
  const { slug } = await params;

  // The articles alongside the project: the listing tab is content, so it
  // belongs in the server HTML rather than in a second round-trip after the
  // page has rendered. `serverFetch` sends no token, so this is the published
  // set — exactly what the tab shows. A failure falls back to the client
  // fetch rather than taking the whole page down with it.
  const [project, articles] = await Promise.all([
    getProjectOr404(slug),
    fetchProjectArticles(slug).catch(() => null),
  ]);

  // Canonicalise: if the URL identifier isn't the project's current slug
  // (e.g. accessed by UUID), 301 to the slug URL.
  if (project.slug && project.slug !== slug) {
    permanentRedirect(`/projects/${project.slug}`);
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectDetailContent
        project={project}
        projectId={project.id}
        articles={articles}
      />
    </main>
  );
}
