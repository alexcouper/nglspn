"use client";

import { useMemo } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { TrophyIcon } from "@heroicons/react/24/solid";
import type { Project } from "@/lib/api";
import { ImageGallery } from "@/components/ImageUpload";
import { TagGroup } from "@/components/TagBadge";

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "badge-warning",
    approved: "badge-success",
    rejected: "badge-error",
  };

  const labels: Record<string, string> = {
    pending: "Pending Review",
    approved: "Approved",
    rejected: "Rejected",
  };

  return (
    <span className={`badge ${styles[status] || "badge-neutral"}`}>
      {labels[status] || status}
    </span>
  );
}

interface ReadOnlyProjectDetailProps {
  project: Project;
  showStatus?: boolean;
}

export function ReadOnlyProjectDetail({ project, showStatus = true }: ReadOnlyProjectDetailProps) {
  const authorName = [project.owner.first_name, project.owner.last_name].filter(Boolean).join(" ") || "Anonymous";

  const tagsByCategory = useMemo(() => {
    if (!project.tags || project.tags.length === 0) return [];

    const groups = new Map<string, { categoryName: string; tags: typeof project.tags }>();
    for (const tag of project.tags) {
      const key = tag.category_slug || "other";
      if (!groups.has(key)) {
        groups.set(key, { categoryName: key.replace(/-/g, " "), tags: [] });
      }
      groups.get(key)!.tags.push(tag);
    }
    return Array.from(groups.values());
  }, [project]);

  return (
    <div className="bg-white rounded-xl border border-border overflow-hidden">
      {/* Images */}
      {project.images && project.images.length > 0 && (
        <div>
          <ImageGallery images={project.images} />
        </div>
      )}

      <div className="p-6 sm:p-8">
        {/* Title + Status */}
        <div className="flex items-start gap-3 mb-4">
          <div className="flex-1">
            <h1 className="text-xl sm:text-2xl font-semibold text-foreground tracking-tight">
              {project.title || "Untitled Project"}
            </h1>
            {project.tagline && (
              <p className="text-muted-foreground text-sm mt-1">{project.tagline}</p>
            )}
          </div>
          {showStatus && <StatusBadge status={project.status} />}
        </div>

        {/* Meta */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground mb-6">
          <a
            href={project.website_url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent transition-colors break-all"
          >
            {project.website_url}
          </a>
          <span className="text-border">|</span>
          <span>
            by{" "}
            <Link
              href={`/users/${project.owner.id}`}
              className="text-foreground hover:text-accent transition-colors"
            >
              {authorName}
            </Link>
          </span>
        </div>

        {/* Winner banner */}
        {project.won_competitions && project.won_competitions.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-2">
            <TrophyIcon className="w-5 h-5 text-amber-500 flex-shrink-0" />
            <p className="text-amber-800 text-sm">
              Winner of{" "}
              {project.won_competitions.map((comp, i) => (
                <span key={comp.slug}>
                  {i > 0 && ", "}
                  <Link
                    href={`/competitions/${comp.slug}`}
                    className="font-medium underline hover:text-amber-900 transition-colors"
                  >
                    {comp.name}
                  </Link>
                </span>
              ))}
            </p>
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Description */}
          <div className="flex-1 min-w-0 space-y-5">
            <article className="markdown">
              <ReactMarkdown>{project.description}</ReactMarkdown>
            </article>

            {/* Status Messages */}
            {showStatus && project.status === "pending" && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                <p className="text-amber-800 text-sm">
                  Your project is currently under review. We&apos;ll notify you once it&apos;s been reviewed.
                </p>
              </div>
            )}

            {showStatus && project.status === "approved" && project.approved_at && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
                <p className="text-emerald-800 text-sm">
                  Approved on{" "}
                  {new Date(project.approved_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </p>
              </div>
            )}
          </div>

          {/* Tags sidebar */}
          {tagsByCategory.length > 0 && (
            <aside className="lg:w-48 flex-shrink-0">
              <div className="lg:sticky lg:top-20 space-y-4">
                {tagsByCategory.map((group) => (
                  <TagGroup
                    key={group.categoryName}
                    categoryName={group.categoryName}
                    tags={group.tags}
                  />
                ))}
              </div>
            </aside>
          )}
        </div>

        {/* Footer */}
        <footer className="pt-6 mt-6 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Submitted{" "}
            {new Date(project.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </footer>
      </div>
    </div>
  );
}
