import { ProjectsListing } from "./ProjectsListing";
import { fetchProjects } from "@/lib/api/server";

export const revalidate = 60;

export default async function ProjectsPage() {
  const data = await fetchProjects({
    sort_by: "title",
    sort_order: "asc",
  }).catch(() => null);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Projects
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Explore what the community is building
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <ProjectsListing
            initialProjects={data?.projects ?? null}
            initialPendingCount={data?.pending_projects_count ?? 0}
          />
        </div>
      </section>
    </main>
  );
}
