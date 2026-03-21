"use client";

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
  initialMostDiscussed: DiscoverProject[];
}

export function ProjectsPage({
  initialCategories,
  initialFeatured,
  initialNewArrivals,
  initialWinners,
  initialMostDiscussed,
}: ProjectsPageProps) {
  const searchParams = useSearchParams();
  const activeCategory = searchParams.get("category");

  const categoriesWithProjects = initialCategories.filter(
    (c) => c.project_count > 0
  );

  return (
    <>
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
              mostDiscussed={initialMostDiscussed}
              categories={categoriesWithProjects}
            />
          )}
        </div>
      </section>
    </>
  );
}
