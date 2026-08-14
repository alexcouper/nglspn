"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api, type Project } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { pickVariant } from "@/lib/utils";

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "badge-warning",
    approved: "badge-success",
    rejected: "badge-error",
  };

  const labels: Record<string, string> = {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
  };

  return (
    <span className={`badge ${styles[status] || "badge-neutral"}`}>
      {labels[status] || status}
    </span>
  );
}

// Read-only: entering needs a round picked per project, which is the project
// page's job.
function CompetitionSummaryLine({ project }: { project: Project }) {
  const standing = project.competition_standing;
  if (!standing || project.is_community_tipoff) return null;

  if (standing.entries.length > 0) {
    return (
      <p className="text-muted-foreground text-xs mt-2">
        In {standing.entries.map((entry) => entry.competition.name).join(", ")}
      </p>
    );
  }

  const open = standing.opportunities.filter(
    (opportunity) => opportunity.eligible
  );
  if (open.length === 0) return null;

  return (
    <p className="text-muted-foreground text-xs mt-2">
      Can enter {open.map((opportunity) => opportunity.competition.name).join(", ")}
    </p>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const mainImage =
    project.images?.find((img) => img.is_main) || project.images?.[0];
  const thumbUrl = mainImage ? pickVariant(mainImage.variants, "thumb") : null;

  return (
    <Link
      href={`/my-projects/${project.id}`}
      className="group block bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all"
    >
      <div className="flex gap-4">
        {mainImage && (
          <div className="relative w-32 aspect-video flex-shrink-0 rounded-lg overflow-hidden bg-slate-100">
            {thumbUrl ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={thumbUrl}
                alt={project.title || "Project image"}
                className="absolute inset-0 w-full h-full object-contain"
                loading="lazy"
              />
            ) : (
              <Image
                src={mainImage.url}
                alt={project.title || "Project image"}
                fill
                className="object-contain"
                sizes="128px"
              />
            )}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h2 className="font-medium text-foreground truncate group-hover:text-accent transition-colors">
                {project.title || "Untitled Project"}
              </h2>
              <p className="text-muted-foreground text-xs truncate mt-0.5">
                {project.website_url}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={project.status} />
            </div>
          </div>
          {project.description && (
            <p className="text-muted-foreground text-sm mt-2 line-clamp-2">
              {project.description}
            </p>
          )}
          <CompetitionSummaryLine project={project} />
        </div>
      </div>
    </Link>
  );
}

export function ProjectsList() {
  const { isReady, isLoading: authLoading } = useRequireAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [tipOffs, setTipOffs] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isReady) return;

    let cancelled = false;

    Promise.all([
      api.myProjects.list(),
      api.myProjects.listTipOffs(),
    ]).then(
      ([projects, tipOffs]) => {
        if (!cancelled) {
          setProjects(projects);
          setTipOffs(tipOffs);
          setIsLoading(false);
        }
      },
      (err) => {
        if (!cancelled) {
          setError(describeApiError(err, "Couldn't load your projects."));
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [isReady]);

  if (authLoading || isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex gap-4">
              <div className="skeleton w-32 aspect-video rounded-lg" />
              <div className="flex-1">
                <div className="skeleton h-5 w-1/3 mb-2" />
                <div className="skeleton h-4 w-1/2 mb-2" />
                <div className="skeleton h-3 w-2/3" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
        <Link href="/" className="text-sm text-accent hover:text-accent-hover transition-colors">
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <>
      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">My Projects</h2>
        {projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-border p-8 text-center">
            <p className="text-muted-foreground text-sm">You haven&apos;t submitted any projects yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </section>

      {tipOffs.length > 0 && (
        <section className="mt-8" data-testid="tip-offs-section">
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Tip Offs</h2>
          <div className="space-y-3">
            {tipOffs.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </section>
      )}

      <div className="mt-8 text-center">
        <Link href="/submit" className="btn-primary">
          {projects.length === 0 ? "Submit your first project" : "Submit a new project"}
        </Link>
      </div>
    </>
  );
}
