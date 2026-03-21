"use client";

import type { CategoryItem, DiscoverProject, WinnerProject } from "@/lib/api";
import { FeaturedSection } from "./sections/FeaturedSection";
import { NewArrivalsSection } from "./sections/NewArrivalsSection";
import { WinnersSection } from "./sections/WinnersSection";
import { CategoryRowsSection } from "./sections/CategoryRowsSection";

interface DiscoverViewProps {
  featured: DiscoverProject[];
  newArrivals: DiscoverProject[];
  winners: WinnerProject[];
  categories: CategoryItem[];
}

export function DiscoverView({
  featured,
  newArrivals,
  winners,
  categories,
}: DiscoverViewProps) {
  return (
    <div className="space-y-10">
      {featured.length > 0 && <FeaturedSection projects={featured} />}
      {newArrivals.length > 0 && <NewArrivalsSection projects={newArrivals} />}
      {winners.length > 0 && <WinnersSection winners={winners} />}
      {categories.length > 0 && <CategoryRowsSection categories={categories} />}
    </div>
  );
}
