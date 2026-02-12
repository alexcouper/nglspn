"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/auth";
import { api, type Project } from "@/lib/api";

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

export function ProjectsList() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
      return;
    }

    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    api.myProjects.list().then(
      (projects) => {
        if (!cancelled) {
          setProjects(projects);
          setIsLoading(false);
        }
      },
      (err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load projects");
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated, router]);

  if (authLoading || isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex gap-4">
              <div className="skeleton w-20 h-20 rounded-lg" />
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
      {projects.length === 0 ? (
        <div className="bg-white rounded-xl border border-border p-8 text-center">
          <p className="text-muted-foreground text-sm">You haven&apos;t submitted any projects yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => {
            const mainImage = project.images?.find((img) => img.is_main) || project.images?.[0];
            return (
              <Link
                key={project.id}
                href={`/my-projects/${project.id}`}
                className="group block bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                <div className="flex gap-4">
                  {mainImage && (
                    <div className="relative w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-slate-100">
                      <Image
                        src={mainImage.url}
                        alt={project.title || "Project image"}
                        fill
                        className="object-cover"
                        sizes="80px"
                      />
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
                      <StatusBadge status={project.status} />
                    </div>
                    {project.description && (
                      <p className="text-muted-foreground text-sm mt-2 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <div className="mt-8 text-center">
        <Link href="/submit" className="btn-primary">
          {projects.length === 0 ? "Submit your first project" : "Submit a new project"}
        </Link>
      </div>
    </>
  );
}
