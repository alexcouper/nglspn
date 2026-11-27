"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import type { DiscoverProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { TipoffBadge } from "@/components/TipoffBadge";

// A project drawn as a hero: its banner over a dark caption. The image-role
// dialog uses it to preview what a hero image will look like.
export function ProjectHeroCard({ project }: { project: DiscoverProject }) {
  const tb = useTranslations("projects.tipoffBadge");
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
            {project.is_community_tipoff && <TipoffBadge size="sm" label={tb("short")} />}
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
