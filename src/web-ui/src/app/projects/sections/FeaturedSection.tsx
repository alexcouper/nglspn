"use client";

import Link from "next/link";

import type { DiscoverProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { TipoffBadge } from "@/components/TipoffBadge";

interface FeaturedSectionProps {
  projects: DiscoverProject[];
}

export function FeaturedSection({ projects }: FeaturedSectionProps) {
  if (projects.length === 0) return null;

  const [main, ...side] = projects;

  return (
    <section>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Large hero card */}
        <LargeHeroCard project={main} />

        {/* Small hero cards */}
        {side.length > 0 && (
          <div className="flex flex-col gap-4">
            {side.slice(0, 2).map((project) => (
              <SmallHeroCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export function LargeHeroCard({ project }: { project: DiscoverProject }) {
  const imageUrl = project.hero_banner_url || project.in_use_image_url;

  return (
    <Link href={`/projects/${project.slug ?? project.id}`} className="group block">
      <div className="card card-interactive overflow-hidden">
        <div className="relative aspect-video">
          {imageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imageUrl}
              alt={project.title}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <GradientPlaceholder id={project.id} className="w-full h-full" />
          )}
        </div>
        <div className="bg-[#0f172a] p-5">
          <div className="flex items-center gap-2">
            {project.category_name && (
              <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                {project.category_name}
              </span>
            )}
            {project.is_community_tipoff && <TipoffBadge size="sm" label="Tipoff" />}
          </div>
          <h3 className="text-lg font-semibold text-white mt-1 group-hover:text-accent-subtle transition-colors">
            {project.title}
          </h3>
          <p className="text-sm text-slate-400 mt-1 line-clamp-2">
            {project.tagline}
          </p>
        </div>
      </div>
    </Link>
  );
}

function SmallHeroCard({ project }: { project: DiscoverProject }) {
  const imageUrl = project.hero_banner_url || project.in_use_image_url;

  return (
    <Link href={`/projects/${project.slug ?? project.id}`} className="group block flex-1">
      <div className="card card-interactive overflow-hidden relative h-full">
        <div className="relative aspect-video h-full">
          {imageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imageUrl}
              alt={project.title}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <GradientPlaceholder id={project.id} className="w-full h-full" />
          )}
          {/* Scrim + gradient overlay */}
          <div className="absolute inset-0 bg-[rgba(15,23,42,0.15)]" />
          <div className="absolute inset-0 bg-gradient-to-t from-[rgba(15,23,42,0.75)] to-transparent" />

          {project.is_community_tipoff && (
            <div className="absolute top-2 right-2">
              <TipoffBadge size="sm" label="Tipoff" />
            </div>
          )}

          {/* Text overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-4">
            {project.category_name && (
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                {project.category_name}
              </span>
            )}
            <h3 className="text-sm font-semibold text-white mt-0.5 group-hover:text-indigo-200 transition-colors">
              {project.title}
            </h3>
            <p className="text-xs text-slate-300 mt-0.5 line-clamp-1">
              {project.tagline}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
