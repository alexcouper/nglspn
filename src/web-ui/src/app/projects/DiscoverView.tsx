"use client";

import type { CategoryItem, DiscoverProject, WinnerProject } from "@/lib/api";
import { FeaturedSection } from "./sections/FeaturedSection";
import { NewArrivalsSection } from "./sections/NewArrivalsSection";
import { RecentTipoffsSection } from "./sections/RecentTipoffsSection";
import { WinnersSection } from "./sections/WinnersSection";
import { CategoryRowsSection } from "./sections/CategoryRowsSection";
import { MostDiscussedSection } from "./sections/MostDiscussedSection";

interface DiscoverViewProps {
  featured: DiscoverProject[];
  newArrivals: DiscoverProject[];
  recentTipoffs: DiscoverProject[];
  winners: WinnerProject[];
  mostDiscussed: DiscoverProject[];
  categories: CategoryItem[];
}

export function DiscoverView({
  featured,
  newArrivals,
  recentTipoffs,
  winners,
  mostDiscussed,
  categories,
}: DiscoverViewProps) {
  return (
    <div className="space-y-10">
      {featured.length > 0 && <FeaturedSection projects={featured} />}
      {newArrivals.length > 0 && <NewArrivalsSection projects={newArrivals} />}
      {winners.length > 0 && <WinnersSection winners={winners} />}
      <RecentTipoffsSection projects={recentTipoffs} />
      {categories.length > 0 && <CategoryRowsSection categories={categories} />}
      {mostDiscussed.length > 0 && (
        <MostDiscussedSection projects={mostDiscussed} />
      )}
    </div>
  );
}
