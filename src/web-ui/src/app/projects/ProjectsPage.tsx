"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { CategoryItem, DiscoverProject, WinnerProject } from "@/lib/api";
import { ListingTabs } from "@/components/ListingTabs";
import { DiscoverView } from "./DiscoverView";
import { CategoryView } from "./CategoryView";

interface ProjectsPageProps {
  initialCategories: CategoryItem[];
  initialFeatured: DiscoverProject[];
  initialNewArrivals: DiscoverProject[];
  initialRecentTipoffs: DiscoverProject[];
  initialWinners: WinnerProject[];
}

export function ProjectsPage({
  initialCategories,
  initialFeatured,
  initialNewArrivals,
  initialRecentTipoffs,
  initialWinners,
}: ProjectsPageProps) {
  const searchParams = useSearchParams();
  const activeCategory = searchParams.get("category");

  const categoriesWithProjects = initialCategories.filter(
    (c) => c.project_count > 0
  );

  return (
    <>
      <ListingTabs
        categories={initialCategories}
        active={
          activeCategory
            ? { kind: "category", slug: activeCategory }
            : { kind: "discover" }
        }
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
              recentTipoffs={initialRecentTipoffs}
              winners={initialWinners}
              categories={categoriesWithProjects}
            />
          )}
        </div>
      </section>

      <div className="sm:hidden sticky bottom-0 z-20 flex justify-center px-4 pb-5 pt-3 pointer-events-none">
        <Link
          href="/create"
          className="pointer-events-auto inline-flex items-center gap-2 text-sm font-medium bg-accent hover:bg-accent-hover text-white px-6 py-3 rounded-full shadow-[0_10px_30px_-5px_rgba(79,70,229,0.5)] ring-1 ring-black/5 transition-all duration-150 hover:-translate-y-0.5"
        >
          Create a project
        </Link>
      </div>
    </>
  );
}
