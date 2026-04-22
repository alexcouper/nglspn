import {
  fetchCategories,
  fetchFeaturedProjects,
  fetchNewArrivals,
  fetchWinners,
} from "@/lib/api/server";
import { ProjectsPage } from "./ProjectsPage";


export default async function PreviewProjectsPage() {
  const [categories, featured, newArrivals, winners] =
    await Promise.all([
      fetchCategories(),
      fetchFeaturedProjects(),
      fetchNewArrivals(),
      fetchWinners(),
    ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectsPage
        initialCategories={categories}
        initialFeatured={featured}
        initialNewArrivals={newArrivals}
        initialWinners={winners}
      />
    </main>
  );
}
