"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { api, ReviewProject, ReviewCompetitionDetailResponse } from "@/lib/api";
import { CompetitionProjects } from "./CompetitionProjects";
import { useBreadcrumbs } from "../BreadcrumbContext";

export default function CompetitionProjectsPage() {
  const params = useParams();
  const competitionId = params.competitionId as string;
  const { setCompetitionName, setProjectTitle } = useBreadcrumbs();

  const [competition, setCompetition] =
    useState<ReviewCompetitionDetailResponse | null>(null);
  const [projects, setProjects] = useState<ReviewProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setProjectTitle("");
  }, [setProjectTitle]);

  useEffect(() => {
    const loadCompetition = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await api.myReview.getCompetition(competitionId);
        setCompetition(response);
        setCompetitionName(response.name);
        const sortedProjects = [...response.projects].sort((a, b) => {
          const rankA = a.my_ranking ?? null;
          const rankB = b.my_ranking ?? null;
          if (rankA === null && rankB === null) return 0;
          if (rankA === null) return 1;
          if (rankB === null) return -1;
          return rankA - rankB;
        });
        setProjects(sortedProjects);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load competition"
        );
      }
      setIsLoading(false);
    };

    loadCompetition();
  }, [competitionId, setCompetitionName]);

  const handleProjectsReorder = useCallback((newProjects: ReviewProject[]) => {
    setProjects(newProjects);
  }, []);

  const handleFinishReview = useCallback(() => {
    if (competition) {
      setCompetition({
        ...competition,
        my_review_status: "completed",
      });
    }
  }, [competition]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-4">
            <div className="flex items-center gap-4">
              <div className="skeleton w-8 h-8 rounded-full" />
              <div className="skeleton w-14 h-14 rounded-lg" />
              <div className="flex-1">
                <div className="skeleton h-4 w-1/3 mb-2" />
                <div className="skeleton h-3 w-1/2" />
              </div>
            </div>
          </div>
        ))}
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

  if (!competition) {
    return <p className="text-muted-foreground text-sm">Competition not found</p>;
  }

  return (
    <CompetitionProjects
      competitionId={competitionId}
      projects={projects}
      isCompleted={competition.my_review_status === "completed"}
      onProjectsReorder={handleProjectsReorder}
      onFinishReview={handleFinishReview}
    />
  );
}
