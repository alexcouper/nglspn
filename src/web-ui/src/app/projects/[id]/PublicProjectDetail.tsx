"use client";

import { useState, useEffect } from "react";
import { ReadOnlyProjectDetail } from "@/app/my-projects/[id]/ReadOnlyProjectDetail";
import { api, type Project } from "@/lib/api";

interface PublicProjectDetailProps {
  projectId: string;
}

export function PublicProjectDetail({ projectId }: PublicProjectDetailProps) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProject = async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await api.projects.get(projectId);
        setProject(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch project");
      }
      setIsLoading(false);
    };

    fetchProject();
  }, [projectId]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-border p-8">
        <div className="skeleton h-6 w-1/3 mb-4" />
        <div className="skeleton h-64 w-full mb-4 rounded-lg" />
        <div className="skeleton h-4 w-2/3 mb-2" />
        <div className="skeleton h-4 w-1/2" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground text-sm">Project not found</p>
      </div>
    );
  }

  return <ReadOnlyProjectDetail project={project} showStatus={false} />;
}
