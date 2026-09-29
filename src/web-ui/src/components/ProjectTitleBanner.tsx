"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { FlagIcon } from "@heroicons/react/24/outline";
import type { Project } from "@/lib/api";
import { getAuthorName } from "@/lib/utils";
import { FollowButton } from "@/components/FollowButton";
import { TipoffBadge } from "@/components/TipoffBadge";
import { ReportProblemDialog } from "@/components/ReportProblemDialog";

interface ProjectTitleBannerProps {
  project: Project;
  iconUrl?: string | null;
}

export function ProjectTitleBanner({ project, iconUrl }: ProjectTitleBannerProps) {
  const displayOwners = project.contributors.filter(
    (c) => c.role === "owner" && c.full_edit && !c.user.is_system_user
  );
  const [isReportOpen, setIsReportOpen] = useState(false);
  // Only a live project has visitors to find it broken. The my-projects
  // preview of a draft renders this banner too, and must not offer it.
  const isReportable = project.status === "approved";

  return (
    <section className="relative bg-white border-b border-border py-10 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto flex gap-4 items-start">
        {/* Icon */}
        {iconUrl && (
          <div className="shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={iconUrl}
              alt={`${project.title} icon`}
              className="w-14 h-14 rounded-lg object-cover border border-border"
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
              {project.title || "Untitled Project"}
            </h1>
            {project.slug && <FollowButton projectSlug={project.slug} />}
          </div>
          {project.is_community_tipoff && (
            <div className="mt-2">
              <TipoffBadge withTooltip />
            </div>
          )}
          {project.tagline && (
            <p className="text-foreground text-base mt-1">
              {project.tagline}
            </p>
          )}
          {project.website_url && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3">
              <a
                href={project.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-base font-medium text-accent hover:text-accent/80 transition-colors break-all"
              >
                {project.website_url.replace(/^https?:\/\//, "")}
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              </a>
              {isReportable && (
                <button
                  type="button"
                  onClick={() => setIsReportOpen(true)}
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <FlagIcon className="w-3.5 h-3.5" aria-hidden="true" />
                  Site not working?
                </button>
              )}
            </div>
          )}
          {displayOwners.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-1 gap-y-1 text-sm text-muted-foreground mt-2">
              <span>by</span>
              {displayOwners.map((contributor, i) => (
                <Fragment key={contributor.user.id}>
                  <Link
                    href={`/users/${contributor.user.id}`}
                    className="text-foreground hover:text-accent transition-colors"
                  >
                    {getAuthorName(contributor.user)}
                  </Link>
                  {i < displayOwners.length - 1 && <span>,</span>}
                </Fragment>
              ))}
            </div>
          )}
        </div>
      </div>
      {isReportable && (
        <ReportProblemDialog
          isOpen={isReportOpen}
          onClose={() => setIsReportOpen(false)}
          projectSlugOrId={project.slug ?? project.id}
          projectTitle={project.title}
          hasMakers={project.contributors.some(
            (c) => c.full_edit && !c.user.is_system_user
          )}
        />
      )}
    </section>
  );
}
