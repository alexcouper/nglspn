"use client";

import Link from "next/link";

import type { DiscoverProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";

interface MostDiscussedSectionProps {
  projects: DiscoverProject[];
}

export function MostDiscussedSection({ projects }: MostDiscussedSectionProps) {
  if (projects.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-semibold text-foreground mb-4">
        Most Discussed
      </h2>
      <div className="space-y-2">
        {projects.slice(0, 5).map((project) => (
          <DiscussedItem key={project.id} project={project} />
        ))}
      </div>
    </section>
  );
}

function DiscussedItem({ project }: { project: DiscoverProject }) {
  const iconUrl = project.icon_url;

  return (
    <Link href={`/projects/${project.slug ?? project.id}`} className="block">
      <div className="card card-interactive p-3 flex items-center gap-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden">
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
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
            {project.tagline}
          </p>
        </div>
        <span className="text-sm font-semibold text-accent flex-shrink-0">
          {project.discussion_count}
        </span>
      </div>
    </Link>
  );
}
