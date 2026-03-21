"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import type { CategoryItem, DiscoverProject } from "@/lib/api";
import { api } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";

type SortOption = "newest" | "name";

interface CategoryViewProps {
  categorySlug: string;
  categories: CategoryItem[];
}

export function CategoryView({ categorySlug, categories }: CategoryViewProps) {
  const [projects, setProjects] = useState<DiscoverProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<SortOption>("newest");
  const requestRef = useRef(0);

  const category = categories.find((c) => c.slug === categorySlug);

  useEffect(() => {
    const id = ++requestRef.current;
    setLoading(true); // eslint-disable-line react-hooks/set-state-in-effect
    api.discover
      .byCategory(categorySlug, sort)
      .then((data) => {
        if (requestRef.current === id) setProjects(data);
      })
      .catch(() => {
        if (requestRef.current === id) setProjects([]);
      })
      .finally(() => {
        if (requestRef.current === id) setLoading(false);
      });
  }, [categorySlug, sort]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {category?.name ?? categorySlug}
          </h2>
          {!loading && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {projects.length} {projects.length === 1 ? "project" : "projects"}
            </p>
          )}
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          className="text-sm border border-border rounded-lg px-3 py-1.5 bg-white text-foreground"
        >
          <option value="newest">Newest</option>
          <option value="name">Name A-Z</option>
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton rounded-xl h-20" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No projects in this category yet.
        </p>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
          {projects.map((project) => (
            <CategoryCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryCard({ project }: { project: DiscoverProject }) {
  const iconUrl = project.icon_url;

  return (
    <Link href={`/projects/${project.id}`} className="block h-full">
      <div className="card card-interactive p-3 flex items-start gap-3 h-full">
        <div className="flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden">
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
