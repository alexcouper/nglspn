"use client";

import Link from "next/link";
import type { Project } from "@/lib/api";
import { getAuthorName } from "@/lib/utils";

interface ProjectTitleBannerProps {
  project: Project;
}

export function ProjectTitleBanner({ project }: ProjectTitleBannerProps) {
  const authorName = getAuthorName(project.owner);

  return (
    <section className="relative bg-white border-b border-border py-10 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
          {project.title || "Untitled Project"}
        </h1>
        {project.tagline && (
          <p className="text-foreground text-base mt-1">
            {project.tagline}
          </p>
        )}
        {project.website_url && (
          <a
            href={project.website_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-3 text-base font-medium text-accent hover:text-accent/80 transition-colors break-all"
          >
            {project.website_url.replace(/^https?:\/\//, "")}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </a>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground mt-2">
          <Link
            href={`/users/${project.owner.id}`}
            className="text-foreground hover:text-accent transition-colors"
          >
            {authorName}
          </Link>
        </div>
      </div>
    </section>
  );
}
