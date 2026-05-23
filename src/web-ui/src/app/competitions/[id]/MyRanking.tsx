"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth";
import { buildLoginPath } from "@/lib/auth-routing";
import { ApiRequestError } from "@/lib/api/base";
import {
  api,
  type ReviewCompetitionDetailResponse,
  type ReviewProject,
} from "@/lib/api";
import { RankingList } from "./RankingList";
import { SubmitRankingDialog } from "./SubmitRankingDialog";

interface MyRankingProps {
  competitionId: string;
  competitionName: string;
  returnPath: string;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "not-assigned" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: ReviewCompetitionDetailResponse; projects: ReviewProject[] };

export function MyRanking({
  competitionId,
  competitionName,
  returnPath,
}: MyRankingProps) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  if (authLoading) {
    return <RankingShell><Skeleton /></RankingShell>;
  }

  if (!isAuthenticated) {
    return (
      <RankingShell>
        <LoggedOutCta returnPath={returnPath} />
      </RankingShell>
    );
  }

  return (
    <RankingShell>
      <RankingLoader competitionId={competitionId} competitionName={competitionName} />
    </RankingShell>
  );
}

function RankingShell({ children }: { children: React.ReactNode }) {
  return (
    <section className="bg-white rounded-xl border border-border p-5 sm:p-6">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-semibold text-foreground">My Ranking</h2>
      </div>
      {children}
    </section>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((i) => (
        <div key={i} className="bg-muted rounded-xl border border-border p-3.5">
          <div className="flex items-center gap-3">
            <div className="skeleton w-7 h-7 rounded-full" />
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

function LoggedOutCta({ returnPath }: { returnPath: string }) {
  const loginHref = buildLoginPath(returnPath);
  const registerHref = `/register?next=${encodeURIComponent(returnPath)}`;
  return (
    <div className="text-center py-4">
      <p className="text-sm text-muted-foreground mb-4">
        Voting is open. Log in to rank these projects and help pick the winner.
      </p>
      <div className="flex flex-col sm:flex-row gap-2 justify-center">
        <Link href={loginHref} className="btn-primary">
          Log in to vote
        </Link>
        <Link href={registerHref} className="btn-secondary">
          Create an account
        </Link>
      </div>
    </div>
  );
}

function NotAssigned() {
  return (
    <div className="text-center py-4">
      <p className="text-sm text-muted-foreground">
        Voting in this competition is open to invited reviewers only.
      </p>
    </div>
  );
}

function RankingLoader({
  competitionId,
  competitionName,
}: {
  competitionId: string;
  competitionName: string;
}) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.myReview.getCompetition(competitionId);
        if (cancelled) return;
        const sorted = [...data.projects].sort((a, b) => {
          const ra = a.my_ranking ?? null;
          const rb = b.my_ranking ?? null;
          if (ra === null && rb === null) return 0;
          if (ra === null) return 1;
          if (rb === null) return -1;
          return ra - rb;
        });
        setState({ kind: "ready", data, projects: sorted });
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setState({ kind: "not-assigned" });
          return;
        }
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Failed to load ranking",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [competitionId]);

  if (state.kind === "loading") return <Skeleton />;
  if (state.kind === "not-assigned") return <NotAssigned />;
  if (state.kind === "error") {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {state.message}
      </div>
    );
  }

  return (
    <RankingActive
      competitionId={competitionId}
      competitionName={competitionName}
      initialData={state.data}
      initialProjects={state.projects}
    />
  );
}

function RankingActive({
  competitionId,
  competitionName,
  initialData,
  initialProjects,
}: {
  competitionId: string;
  competitionName: string;
  initialData: ReviewCompetitionDetailResponse;
  initialProjects: ReviewProject[];
}) {
  const [reviewStatus, setReviewStatus] = useState(initialData.my_review_status);
  const [projects, setProjects] = useState(initialProjects);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isCompleted = reviewStatus === "completed";
  const isEnded = reviewStatus === "ended";
  const isInProgress = reviewStatus === "in_progress";
  const readOnly = !isInProgress;

  const persistOrder = useCallback(
    (next: ReviewProject[]) => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = setTimeout(async () => {
        setIsSaving(true);
        setSaveError(null);
        try {
          await api.myReview.updateRankings(
            competitionId,
            next.map((p) => p.id)
          );
        } catch {
          setSaveError("Failed to save rankings");
        } finally {
          setIsSaving(false);
        }
      }, 500);
    },
    [competitionId]
  );

  const handleReorder = useCallback(
    (next: ReviewProject[]) => {
      setProjects(next);
      persistOrder(next);
    },
    [persistOrder]
  );

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setStatusError(null);
    try {
      await api.myReview.updateStatus(competitionId, "completed");
      setReviewStatus("completed");
      setShowSubmitDialog(false);
    } catch {
      setStatusError("Failed to submit ranking");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReopen = async () => {
    setStatusError(null);
    try {
      await api.myReview.updateStatus(competitionId, "in_progress");
      setReviewStatus("in_progress");
    } catch {
      setStatusError("Failed to reopen ranking");
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <StatusPill
          isCompleted={isCompleted}
          isEnded={isEnded}
          isInProgress={isInProgress}
        />
        {isInProgress && (
          <span className="text-xs text-muted-foreground" aria-live="polite">
            {isSaving ? "Saving…" : saveError ? (
              <span className="text-red-500">{saveError}</span>
            ) : null}
          </span>
        )}
      </div>

      {isInProgress && (
        <p className="text-xs text-muted-foreground mb-4">
          Drag handles or use the up/down buttons to rank projects. Order them
          from most to least worthy of the {competitionName} prize.
        </p>
      )}

      <RankingList
        projects={projects}
        readOnly={readOnly}
        variant="L"
        onReorder={handleReorder}
      />

      {statusError && (
        <p className="mt-3 text-sm text-red-600">{statusError}</p>
      )}

      {isInProgress && (
        <div className="mt-6 pt-5 border-t border-border">
          <button
            type="button"
            onClick={() => setShowSubmitDialog(true)}
            disabled={projects.length === 0}
            className="w-full btn-primary py-3"
          >
            Submit Ranking
          </button>
        </div>
      )}

      {isCompleted && (
        <div className="mt-6 pt-5 border-t border-border flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            Your ranking is locked in.
          </p>
          <button
            type="button"
            onClick={handleReopen}
            className="text-sm text-accent hover:underline"
          >
            Reopen ranking
          </button>
        </div>
      )}

      <SubmitRankingDialog
        isOpen={showSubmitDialog}
        onConfirm={handleSubmit}
        onCancel={() => setShowSubmitDialog(false)}
        isSubmitting={isSubmitting}
      />
    </>
  );
}

function StatusPill({
  isCompleted,
  isEnded,
  isInProgress,
}: {
  isCompleted: boolean;
  isEnded: boolean;
  isInProgress: boolean;
}) {
  if (isCompleted) {
    return (
      <span className="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
        Submitted
      </span>
    );
  }
  if (isEnded) {
    return (
      <span className="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
        Voting ended
      </span>
    );
  }
  if (isInProgress) {
    return (
      <span className="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200">
        In progress
      </span>
    );
  }
  return null;
}
