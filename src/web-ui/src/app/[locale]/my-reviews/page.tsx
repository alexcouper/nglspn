"use client";

import { useState, useEffect } from "react";
import { api, ReviewCompetition } from "@/lib/api";
import { CompetitionsList } from "./CompetitionsList";
import { useBreadcrumbs } from "./BreadcrumbContext";

export default function MyReviewsPage() {
  const { clear } = useBreadcrumbs();
  const [competitions, setCompetitions] = useState<ReviewCompetition[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    clear();
  }, [clear]);

  useEffect(() => {
    const loadCompetitions = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await api.myReview.getCompetitions();
        setCompetitions(response.competitions);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load competitions"
        );
      }
      setIsLoading(false);
    };

    loadCompetitions();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex items-start gap-4">
              <div className="skeleton w-11 h-11 rounded-full" />
              <div className="flex-1">
                <div className="skeleton h-5 w-1/3 mb-2" />
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

  return <CompetitionsList competitions={competitions} />;
}
