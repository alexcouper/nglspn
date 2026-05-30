import {
  fetchCategories,
  fetchFeaturedProjects,
  fetchMostDiscussed,
  fetchNewArrivals,
  fetchRecentTipoffs,
  fetchWinners,
} from "@/lib/api/server";
import { ProjectsPage } from "./ProjectsPage";


export default async function PreviewProjectsPage() {
  const [categories, featured, newArrivals, recentTipoffs, winners, mostDiscussed] =
    await Promise.all([
      fetchCategories(),
      fetchFeaturedProjects(),
      fetchNewArrivals(),
      fetchRecentTipoffs(),
      fetchWinners(),
      fetchMostDiscussed(),
    ]);

  return (
    <main className="min-h-screen bg-muted pt-14">
      <ProjectsPage
        initialCategories={categories}
        initialFeatured={featured}
        initialNewArrivals={newArrivals}
        initialRecentTipoffs={recentTipoffs}
        initialWinners={winners}
        initialMostDiscussed={mostDiscussed}
      />
    </main>
  );
}
