"use client";

import type { DiscoverProject } from "@/lib/api";
import { ProjectTile } from "@/components/ProjectTile";
import { HorizontalScroll } from "../HorizontalScroll";

interface NewArrivalsSectionProps {
  projects: DiscoverProject[];
}

export function NewArrivalsSection({ projects }: NewArrivalsSectionProps) {
  if (projects.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-foreground">
          New Arrivals
        </h2>
      </div>
      <HorizontalScroll>
        {projects.map((project) => (
          <ArrivalCard key={project.id} project={project} />
        ))}
      </HorizontalScroll>
    </section>
  );
}

export function ArrivalCard({ project }: { project: DiscoverProject }) {
  return (
    <div className="flex-shrink-0 w-[240px]">
      <ProjectTile
        id={project.id}
        href={`/projects/${project.slug ?? project.id}`}
        imageUrl={project.in_use_image_url || project.hero_banner_url || null}
        title={project.title}
        tagline={project.tagline}
        categoryName={project.category_name}
      />
    </div>
  );
}
