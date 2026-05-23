"use client";

import { useRef, useState, useCallback } from "react";
import Link from "next/link";
import { buildLoginPath } from "@/lib/auth-routing";
import {
  api,
  type ReviewCompetitionDetailResponse,
  type ReviewProject,
} from "@/lib/api";
import { RankingList } from "./RankingList";
import { SubmitRankingDialog } from "./SubmitRankingDialog";
import { useVariantPref, type RankingVariant } from "./useVariantPref";
import type { ReviewState } from "./types";

interface MyRankingProps {
  competitionId: string;
  competitionName: string;
  returnPath: string;
  reviewState: ReviewState;
}

export function MyRanking(props: MyRankingProps) {
  const { reviewState } = props;

  if (reviewState.kind === "loading") {
    return <RankingShell><Skeleton /></RankingShell>;
  }

  if (reviewState.kind === "logged-out") {
    return <CompactLoggedOutCta returnPath={props.returnPath} />;
  }

  if (reviewState.kind === "not-assigned") {
    return null;
  }

  if (reviewState.kind === "error") {
    return (
      <RankingShell>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {reviewState.message}
        </div>
      </RankingShell>
    );
  }

  return (
    <RankingActive
      competitionId={props.competitionId}
      competitionName={props.competitionName}
      initialData={reviewState.data}
      initialProjects={reviewState.projects}
    />
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
    <div className="space-y-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="bg-muted rounded-xl border border-border p-4">
          <div className="flex items-center gap-4">
            <div className="skeleton w-10 h-10 rounded-full" />
            <div className="skeleton w-24 h-24 rounded-lg" />
            <div className="flex-1">
              <div className="skeleton h-4 w-1/3 mb-2" />
              <div className="skeleton h-3 w-2/3 mb-2" />
              <div className="skeleton h-3 w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function CompactLoggedOutCta({ returnPath }: { returnPath: string }) {
  const loginHref = buildLoginPath(returnPath);
  const registerHref = `/register?next=${encodeURIComponent(returnPath)}`;
  return (
    <section className="bg-white rounded-xl border border-border p-5 sm:p-6">
      <p className="text-sm text-muted-foreground mb-4">
        Voting is open. Log in to rank these projects and help pick the winner.
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <Link href={loginHref} className="btn-primary">
          Log in to vote
        </Link>
        <Link href={registerHref} className="btn-secondary">
          Create an account
        </Link>
      </div>
    </section>
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
  const { variant, setVariant, toggleEnabled } = useVariantPref();

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
    <section className="bg-white rounded-xl border border-border p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-foreground">My Ranking</h2>
          <StatusPill
            isCompleted={isCompleted}
            isEnded={isEnded}
            isInProgress={isInProgress}
          />
        </div>
        <div className="flex items-center gap-3 ml-auto">
          {isInProgress && (
            <span
              className="text-xs text-muted-foreground"
              aria-live="polite"
            >
              {isSaving ? "Saving…" : saveError ? (
                <span className="text-red-500">{saveError}</span>
              ) : null}
            </span>
          )}
          {toggleEnabled && <VariantToggle value={variant} onChange={setVariant} />}
        </div>
      </div>

      {isInProgress && (
        <p className="text-xs text-muted-foreground mb-4">
          Drag the cards or use the up/down buttons to rank projects. Order them
          from most to least worthy of the {competitionName} prize.
        </p>
      )}

      <RankingList
        projects={projects}
        readOnly={readOnly}
        variant={variant}
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
    </section>
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

function VariantToggle({
  value,
  onChange,
}: {
  value: RankingVariant;
  onChange: (next: RankingVariant) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Ranking card layout"
      className="inline-flex items-center gap-1 text-xs"
    >
      <span className="text-muted-foreground" aria-hidden="true">Layout</span>
      {(["L", "R"] as const).map((v) => (
        <button
          key={v}
          type="button"
          onClick={() => onChange(v)}
          aria-pressed={value === v}
          aria-label={v === "L" ? "Controls on the left" : "Controls on the right"}
          className={`w-7 h-6 rounded border text-xs font-medium transition-colors ${
            value === v
              ? "bg-accent text-white border-accent"
              : "bg-white text-muted-foreground border-border hover:border-slate-300"
          }`}
        >
          {v}
        </button>
      ))}
    </div>
  );
}
