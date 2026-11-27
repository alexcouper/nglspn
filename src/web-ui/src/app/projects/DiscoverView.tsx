"use client";

import type { CategoryItem, DiscoverProject, WinnerProject } from "@/lib/api";
import type { DiscoverTop } from "@/lib/discover-top";
import { RecentSection } from "./sections/RecentSection";
import { SpotlightSection } from "./sections/SpotlightSection";
import { NewArrivalsSection } from "./sections/NewArrivalsSection";
import { RecentTipoffsSection } from "./sections/RecentTipoffsSection";
import { WinnersSection } from "./sections/WinnersSection";
import { CategoryRowsSection } from "./sections/CategoryRowsSection";

interface DiscoverViewProps {
  top: DiscoverTop;
  newArrivals: DiscoverProject[];
  recentTipoffs: DiscoverProject[];
  winners: WinnerProject[];
  categories: CategoryItem[];
}

export function DiscoverView({
  top,
  newArrivals,
  recentTipoffs,
  winners,
  categories,
}: DiscoverViewProps) {
  return (
    <div className="space-y-10">
      <RecentSection lead={top.lead} second={top.second} slot={top.slot} />
      <SpotlightSection articles={top.spotlight} />
      {newArrivals.length > 0 && <NewArrivalsSection projects={newArrivals} />}
      {winners.length > 0 && <WinnersSection winners={winners} />}
      <RecentTipoffsSection projects={recentTipoffs} />
      {categories.length > 0 && <CategoryRowsSection categories={categories} />}
    </div>
  );
}
