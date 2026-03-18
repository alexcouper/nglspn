"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AdminProjectListItem } from "@/lib/api/admin";

type FilterType = "" | "missing" | "proposed";

function StatusBadge({ status }: { status: string }) {
  if (status === "active") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        Active
      </span>
    );
  }
  if (status === "proposed") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
        Proposed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
      Missing
    </span>
  );
}

export default function AdminProjectsPage() {
  const [projects, setProjects] = useState<AdminProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("");
  const [error, setError] = useState("");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.admin.listProjects(filter || undefined);
      setProjects(result.projects);
    } catch {
      setError("Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-foreground">
          Project Image Management
        </h1>
        <div className="flex gap-2">
          {(
            [
              ["", "All"],
              ["missing", "Missing Images"],
              ["proposed", "Has Proposals"],
            ] as [FilterType, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                filter === value
                  ? "bg-accent text-white border-accent"
                  : "bg-white text-foreground border-border hover:border-muted-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">
          No projects match this filter.
        </p>
      ) : (
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">
                  Project
                </th>
                <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">
                  Owner
                </th>
                <th className="text-center text-xs font-medium text-muted-foreground px-4 py-3">
                  Icon
                </th>
                <th className="text-center text-xs font-medium text-muted-foreground px-4 py-3">
                  Main Image
                </th>
                <th className="text-center text-xs font-medium text-muted-foreground px-4 py-3">
                  Winner
                </th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr
                  key={project.id}
                  className="border-b border-border last:border-b-0 hover:bg-muted/20 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/projects/${project.id}`}
                      className="text-sm font-medium text-foreground hover:text-accent transition-colors"
                    >
                      {project.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-muted-foreground">
                      {project.owner_email}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge
                      status={project.image_completeness.icon}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge
                      status={project.image_completeness.main_image}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    {project.image_completeness.winner_composite !==
                    null ? (
                      <StatusBadge
                        status={
                          project.image_completeness.winner_composite
                        }
                      />
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        —
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
