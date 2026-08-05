"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { buildLoginPath } from "@/lib/auth-routing";
import {
  api,
  type ReviewCompetitionDetailResponse,
  type ReviewProject,
} from "@/lib/api";
import { PoolList, RankingList } from "./RankingList";
import { SubmitRankingDialog } from "./SubmitRankingDialog";
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
      initialRanked={reviewState.ranked}
      initialPool={reviewState.pool}
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

type RankingTab = "ranked" | "pool";

function RankingActive({
  competitionId,
  competitionName,
  initialData,
  initialRanked,
  initialPool,
}: {
  competitionId: string;
  competitionName: string;
  initialData: ReviewCompetitionDetailResponse;
  initialRanked: ReviewProject[];
  initialPool: ReviewProject[];
}) {
  const [reviewStatus, setReviewStatus] = useState(initialData.my_review_status);
  const [ranked, setRanked] = useState(initialRanked);
  const [pool, setPool] = useState(initialPool);
  const [activeTab, setActiveTab] = useState<RankingTab>("ranked");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingIdsRef = useRef<string[] | null>(null);

  // The server's pool order for this reviewer. Kept so a removed project drops
  // back into the same place it would occupy on a fresh load.
  const poolOrderRef = useRef(
    new Map(
      [...initialPool, ...initialRanked].map((project, index) => [
        project.id,
        index,
      ])
    )
  );

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, []);

  const isCompleted = reviewStatus === "completed";
  const isEnded = reviewStatus === "ended";
  const isInProgress = reviewStatus === "in_progress";
  const readOnly = !isInProgress;

  const saveNow = useCallback(
    async (projectIds: string[]) => {
      setIsSaving(true);
      setSaveError(null);
      try {
        await api.myReview.updateRankings(competitionId, projectIds);
      } catch {
        setSaveError("Failed to save rankings");
      } finally {
        setIsSaving(false);
      }
    },
    [competitionId]
  );

  const persistOrder = useCallback(
    (next: ReviewProject[]) => {
      pendingIdsRef.current = next.map((p) => p.id);
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = setTimeout(() => {
        saveTimeoutRef.current = null;
        const ids = pendingIdsRef.current;
        pendingIdsRef.current = null;
        if (ids) void saveNow(ids);
      }, 500);
    },
    [saveNow]
  );

  /** Write any debounced change immediately; used before submitting. */
  const flushPendingSave = useCallback(async () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    const ids = pendingIdsRef.current;
    pendingIdsRef.current = null;
    if (ids) await saveNow(ids);
  }, [saveNow]);

  const handleReorder = useCallback(
    (next: ReviewProject[]) => {
      setRanked(next);
      persistOrder(next);
    },
    [persistOrder]
  );

  const handleAdd = useCallback(
    (project: ReviewProject) => {
      const next = [...ranked, project];
      setRanked(next);
      setPool(pool.filter((p) => p.id !== project.id));
      persistOrder(next);
    },
    [ranked, pool, persistOrder]
  );

  const handleRemove = useCallback(
    (project: ReviewProject) => {
      const next = ranked.filter((p) => p.id !== project.id);
      setRanked(next);
      setPool(insertIntoPool(pool, project, poolOrderRef.current));
      persistOrder(next);
    },
    [ranked, pool, persistOrder]
  );

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setStatusError(null);
    try {
      await flushPendingSave();
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
        {isInProgress && (
          <span
            className="text-xs text-muted-foreground ml-auto"
            aria-live="polite"
          >
            {isSaving ? "Saving…" : saveError ? (
              <span className="text-red-500">{saveError}</span>
            ) : null}
          </span>
        )}
      </div>

      {isInProgress && (
        <p className="text-xs text-muted-foreground mb-4">
          Rank your favourite projects, best first. Add the
          ones you want to back for the {competitionName} prize and leave the
          rest unranked.
        </p>
      )}

      <div className="flex gap-2 mb-4 lg:hidden" role="tablist">
        <TabButton
          isActive={activeTab === "ranked"}
          onClick={() => setActiveTab("ranked")}
        >
          My ranking ({ranked.length})
        </TabButton>
        <TabButton
          isActive={activeTab === "pool"}
          onClick={() => setActiveTab("pool")}
        >
          Unranked ({pool.length})
        </TabButton>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div
          data-testid="ranked-panel"
          className={`min-w-0 ${activeTab === "ranked" ? "" : "hidden lg:block"}`}
        >
          <h3 className="hidden lg:block text-sm font-medium text-foreground mb-3">
            My ranking ({ranked.length})
          </h3>
          <RankingList
            projects={ranked}
            readOnly={readOnly}
            onReorder={handleReorder}
            onRemove={readOnly ? undefined : handleRemove}
          />
        </div>

        <div
          data-testid="pool-panel"
          className={`min-w-0 ${activeTab === "pool" ? "" : "hidden lg:block"}`}
        >
          <h3 className="hidden lg:block text-sm font-medium text-foreground mb-3">
            Unranked ({pool.length})
          </h3>
          <PoolList projects={pool} readOnly={readOnly} onAdd={handleAdd} />
        </div>
      </div>

      {statusError && (
        <p className="mt-3 text-sm text-red-600">{statusError}</p>
      )}

      {isInProgress && (
        <div className="mt-6 pt-5 border-t border-border">
          <button
            type="button"
            onClick={() => setShowSubmitDialog(true)}
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
        rankedCount={ranked.length}
        onConfirm={handleSubmit}
        onCancel={() => setShowSubmitDialog(false)}
        isSubmitting={isSubmitting}
      />
    </section>
  );
}

function TabButton({
  isActive,
  onClick,
  children,
}: {
  isActive: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={onClick}
      className={`flex-1 text-sm px-3 py-2 rounded-lg border transition-colors ${
        isActive
          ? "bg-accent/10 border-accent/30 text-accent font-medium"
          : "bg-white border-border text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}

/**
 * Put a removed project back where a fresh page load would show it, using the
 * server's pool order. Projects that arrived already ranked have no server pool
 * position, so they go last until the next load.
 */
function insertIntoPool(
  pool: ReviewProject[],
  project: ReviewProject,
  order: Map<string, number>
): ReviewProject[] {
  const positionOf = (id: string) => order.get(id) ?? Number.MAX_SAFE_INTEGER;
  const target = positionOf(project.id);
  const index = pool.findIndex((p) => positionOf(p.id) > target);
  if (index === -1) return [...pool, project];
  return [...pool.slice(0, index), project, ...pool.slice(index)];
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

