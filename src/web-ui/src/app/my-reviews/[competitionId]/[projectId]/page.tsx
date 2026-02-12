"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  api,
  ReviewProjectDetail as ReviewProjectDetailType,
} from "@/lib/api";
import { ReadOnlyProjectDetail } from "@/app/my-projects/[id]/ReadOnlyProjectDetail";
import { useBreadcrumbs } from "../../BreadcrumbContext";

export default function ReviewProjectDetailPage() {
  const params = useParams();
  const competitionId = params.competitionId as string;
  const projectId = params.projectId as string;
  const { setCompetitionName, setProjectTitle } = useBreadcrumbs();

  const [project, setProject] = useState<ReviewProjectDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError("");
      try {
        const [projectData, competitionData] = await Promise.all([
          api.myReview.getProject(projectId),
          api.myReview.getCompetition(competitionId),
        ]);
        setProject(projectData);
        setCompetitionName(competitionData.name);
        setProjectTitle(projectData.title);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      }
      setIsLoading(false);
    };

    fetchData();
  }, [projectId, competitionId, setCompetitionName, setProjectTitle]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-border p-8">
        <div className="skeleton h-6 w-1/3 mb-4" />
        <div className="skeleton h-48 w-full mb-4 rounded-lg" />
        <div className="skeleton h-4 w-2/3 mb-2" />
        <div className="skeleton h-4 w-1/2" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error}
      </div>
    );
  }

  if (!project) {
    return <p className="text-muted-foreground text-sm">Project not found</p>;
  }

  return <ReadOnlyProjectDetail project={project} showStatus={false} />;
}
