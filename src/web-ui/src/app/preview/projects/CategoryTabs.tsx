"use client";

import Link from "next/link";
import type { CategoryItem } from "@/lib/api";

interface CategoryTabsProps {
  categories: CategoryItem[];
  activeCategory: string | null;
}

export function CategoryTabs({ categories, activeCategory }: CategoryTabsProps) {
  return (
    <div className="sticky top-14 z-10 bg-white border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <nav className="flex gap-6 overflow-x-auto scrollbar-hide" aria-label="Category tabs">
          <TabLink
            href="/preview/projects"
            active={!activeCategory}
            label="Discover"
          />
          {categories.map((cat) => (
            <TabLink
              key={cat.id}
              href={`/preview/projects?category=${cat.slug}`}
              active={activeCategory === cat.slug}
              label={cat.name}
            />
          ))}
        </nav>
      </div>
    </div>
  );
}

function TabLink({
  href,
  active,
  label,
}: {
  href: string;
  active: boolean;
  label: string;
}) {
  return (
    <Link
      href={href}
      className={`whitespace-nowrap py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-accent text-accent"
          : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
      }`}
    >
      {label}
    </Link>
  );
}
