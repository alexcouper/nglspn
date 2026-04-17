"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { CategoryItem, DiscoverProject, WinnerProject } from "@/lib/api";
import { CategoryTabs } from "./CategoryTabs";
import { DiscoverView } from "./DiscoverView";
import { CategoryView } from "./CategoryView";

interface ProjectsPageProps {
  initialCategories: CategoryItem[];
  initialFeatured: DiscoverProject[];
  initialNewArrivals: DiscoverProject[];
  initialWinners: WinnerProject[];
}

export function ProjectsPage({
  initialCategories,
  initialFeatured,
  initialNewArrivals,
  initialWinners,
}: ProjectsPageProps) {
  const searchParams = useSearchParams();
  const activeCategory = searchParams.get("category");

  const categoriesWithProjects = initialCategories.filter(
    (c) => c.project_count > 0
  );

  return (
    <>
      <CategoryTabs
        categories={categoriesWithProjects}
        activeCategory={activeCategory}
      />

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          {activeCategory ? (
            <CategoryView
              categorySlug={activeCategory}
              categories={initialCategories}
            />
          ) : (
            <DiscoverView
              featured={initialFeatured}
              newArrivals={initialNewArrivals}
              winners={initialWinners}
              categories={categoriesWithProjects}
            />
          )}
        </div>
      </section>

      <Link
        href="/submit"
        className="sm:hidden fixed bottom-4 left-4 right-4 z-20 text-center text-sm font-medium bg-accent hover:bg-accent-hover text-white px-4 py-3 rounded-lg shadow-lg transition-colors duration-150"
      >
        Submit a project
      </Link>
    </>
  );
}
