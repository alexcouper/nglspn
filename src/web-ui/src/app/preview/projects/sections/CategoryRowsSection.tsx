"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type { CategoryItem, DiscoverProject } from "@/lib/api";
import { api } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { HorizontalScroll } from "../HorizontalScroll";

interface CategoryRowsSectionProps {
  categories: CategoryItem[];
}

export function CategoryRowsSection({ categories }: CategoryRowsSectionProps) {
  if (categories.length === 0) return null;

  return (
    <div className="space-y-8">
      {categories.map((cat) => (
        <CategoryRow key={cat.id} category={cat} />
      ))}
    </div>
  );
}

function CategoryRow({ category }: { category: CategoryItem }) {
  const [projects, setProjects] = useState<DiscoverProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.discover
      .byCategory(category.slug, "newest")
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, [category.slug]);

  if (!loading && projects.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-foreground">
          {category.name}
        </h2>
        <Link
          href={`/preview/projects?category=${category.slug}`}
          className="text-sm text-accent hover:text-accent-hover font-medium"
        >
          See all
        </Link>
      </div>
      {loading ? (
        <div className="flex gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="w-[200px] h-16 skeleton rounded-xl flex-shrink-0" />
          ))}
        </div>
      ) : (
        <HorizontalScroll>
          {projects.map((project) => (
            <IconCard key={project.id} project={project} iconSize={44} />
          ))}
        </HorizontalScroll>
      )}
    </section>
  );
}

function IconCard({
  project,
  iconSize,
}: {
  project: DiscoverProject;
  iconSize: number;
}) {
  const iconUrl = project.icon_url;

  return (
    <Link
      href={`/projects/${project.id}`}
      className="block flex-shrink-0 w-[200px]"
    >
      <div className="card card-interactive p-3 flex items-start gap-3">
        <div
          className="flex-shrink-0 rounded-lg overflow-hidden"
          style={{ width: iconSize, height: iconSize }}
        >
          {iconUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={iconUrl}
              alt={project.title}
              className="object-cover w-full h-full"
            />
          ) : (
            <GradientPlaceholder
              id={project.id}
              className="w-full h-full rounded-lg"
            />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-foreground truncate">
            {project.title}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
            {project.tagline}
          </p>
        </div>
      </div>
    </Link>
  );
}
