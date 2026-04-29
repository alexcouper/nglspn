"use client";

import Link from "next/link";

import type { DiscoverProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { TipoffBadge } from "@/components/TipoffBadge";
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
  const imageUrl = project.in_use_image_url || project.hero_banner_url;

  return (
    <Link
      href={`/projects/${project.slug ?? project.id}`}
      className="flex flex-shrink-0 w-[240px]"
    >
      <div className="card card-interactive overflow-hidden flex flex-col w-full">
        <div className="relative aspect-[4/3]">
          {imageUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imageUrl}
                alt={project.title}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,0,0,0.15)] to-transparent" />
            </>
          ) : (
            <GradientPlaceholder id={project.id} className="w-full h-full" />
          )}
        </div>
        <div className="p-3.5 flex-1">
          <div className="flex items-center gap-2">
            {project.category_name && (
              <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
                {project.category_name}
              </span>
            )}
            {project.community_owned && <TipoffBadge size="sm" label="Tipoff" />}
          </div>
          <h3 className="text-sm font-medium text-foreground mt-0.5 truncate">
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
