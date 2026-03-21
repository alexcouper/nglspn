import {
  fetchCategories,
  fetchFeaturedProjects,
  fetchNewArrivals,
  fetchWinners,
  fetchMostDiscussed,
} from "@/lib/api/server";
import { ProjectsPage } from "./ProjectsPage";

export const revalidate = 3600;

export default async function PreviewProjectsPage() {
  const [categories, featured, newArrivals, winners, mostDiscussed] =
    await Promise.all([
      fetchCategories().catch(() => []),
      fetchFeaturedProjects().catch(() => []),
      fetchNewArrivals().catch(() => []),
      fetchWinners().catch(() => []),
      fetchMostDiscussed().catch(() => []),
    ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectsPage
        initialCategories={categories}
        initialFeatured={featured}
        initialNewArrivals={newArrivals}
        initialWinners={winners}
        initialMostDiscussed={mostDiscussed}
      />
    </main>
  );
}
