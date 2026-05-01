"use client";

import Link from "next/link";

import type { DiscoverProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { Tooltip } from "@/components/Tooltip";
import { TIPOFF_EXPLAINER } from "@/lib/constants";
import { HorizontalScroll } from "../HorizontalScroll";

// Hide the section unless there are enough tip-offs to make a row worth its
// own heading. With fewer than this they look stranded; bump as the volume
// grows.
const MIN_TIPOFFS_TO_DISPLAY = 3;

interface RecentTipoffsSectionProps {
  projects: DiscoverProject[];
}

export function RecentTipoffsSection({ projects }: RecentTipoffsSectionProps) {
  if (projects.length < MIN_TIPOFFS_TO_DISPLAY) return null;

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-lg font-semibold text-foreground">
          Recent Tipoffs
        </h2>
        <Tooltip content={TIPOFF_EXPLAINER}>
          <button
            type="button"
            aria-label="What is a community tip-off?"
            className="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-900 border border-amber-200 hover:bg-amber-200 transition-colors"
          >
            ?
          </button>
        </Tooltip>
      </div>
      <HorizontalScroll>
        {projects.map((project) => (
          <TipoffCard key={project.id} project={project} />
        ))}
      </HorizontalScroll>
    </section>
  );
}

function TipoffCard({ project }: { project: DiscoverProject }) {
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
          {project.category_name && (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
              {project.category_name}
            </span>
          )}
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
