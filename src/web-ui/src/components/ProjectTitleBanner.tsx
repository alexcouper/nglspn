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
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground mt-3">
          <Link
            href={`/users/${project.owner.id}`}
            className="text-foreground hover:text-accent transition-colors"
          >
            {authorName}
          </Link>
          {project.website_url && (
            <>
              <span className="text-border">·</span>
              <a
                href={project.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-accent transition-colors break-all"
              >
                {project.website_url.replace(/^https?:\/\//, "")}
              </a>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
