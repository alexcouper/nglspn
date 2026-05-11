"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/contexts/auth";
import { useNotifications } from "@/contexts/notifications";
import { api } from "@/lib/api";
import type { Discussion, Reply } from "@/lib/api";
import { DiscussionList } from "@/app/projects/[slug]/discussions/DiscussionList";
import { NewDiscussionForm } from "@/app/projects/[slug]/discussions/NewDiscussionForm";
import { buildLoginPath } from "@/lib/auth-routing";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

interface InlineDiscussionsProps {
  projectId: string;
}

function findCommentInTree(
  discussions: Discussion[],
  commentId: string
): { rootId: string; isRoot: boolean } | null {
  for (const d of discussions) {
    if (d.id === commentId) {
      return { rootId: d.id, isRoot: true };
    }
    for (const r of d.replies) {
      if (r.id === commentId) {
        return { rootId: d.id, isRoot: false };
      }
    }
  }
  return null;
}

function DiscussionsSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="bg-white rounded-xl border border-border p-5"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="skeleton h-4 w-24 rounded" />
            <div className="skeleton h-3 w-16 rounded" />
          </div>
          <div className="skeleton h-4 w-full rounded mb-2" />
          <div className="skeleton h-4 w-2/3 rounded" />
        </div>
      ))}
    </div>
  );
}

export function InlineDiscussions({ projectId }: InlineDiscussionsProps) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { markThreadRead, markThreadByComment } = useNotifications();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const commentParam = searchParams.get("comment");
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [fetched, setFetched] = useState(false);
  const [error, setError] = useState("");
  const [staleToast, setStaleToast] = useState(false);
  const processedCommentRef = useRef<string | null>(null);

  const refreshDiscussions = useCallback(async (): Promise<Discussion[]> => {
    const data = await api.discussions.list(projectId);
    setDiscussions(data);
    return data;
  }, [projectId]);

  useEffect(() => {
    if (!isAuthenticated || authLoading) return;
    let cancelled = false;
    queueMicrotask(() => {
      refreshDiscussions()
        .catch(() => {
          if (!cancelled) setError("Failed to load discussions");
        })
        .finally(() => {
          if (!cancelled) setFetched(true);
        });
    });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, authLoading, refreshDiscussions]);

  // Resolve the comment param to {rootId, isRoot} from currently-loaded data.
  const anchor = useMemo(() => {
    if (!commentParam || !fetched) return null;
    return findCommentInTree(discussions, commentParam);
  }, [commentParam, fetched, discussions]);

  // Click-through side effects: when a `?comment=<id>` arrives, find the
  // comment in the loaded data; if missing, refetch once (the user may have
  // been viewing a stale list) and re-check on the fresh data. Highlight is
  // handled in children via anchorCommentId; here we mark the thread read
  // and surface a "no longer available" toast as needed.
  useEffect(() => {
    if (!commentParam || !fetched) return;
    if (processedCommentRef.current === commentParam) return;
    if (anchor) {
      processedCommentRef.current = commentParam;
      void markThreadRead(anchor.rootId);
      return;
    }
    // Anchor not found in current data — refetch once, then decide.
    processedCommentRef.current = commentParam;
    let cancelled = false;
    const showIds: number[] = [];
    queueMicrotask(() => {
      refreshDiscussions()
        .then((fresh) => {
          if (cancelled) return;
          const freshAnchor = findCommentInTree(fresh, commentParam);
          if (freshAnchor) {
            void markThreadRead(freshAnchor.rootId);
            return;
          }
          // Truly unavailable.
          void markThreadByComment(commentParam);
          showIds.push(window.setTimeout(() => setStaleToast(true), 0));
          showIds.push(window.setTimeout(() => setStaleToast(false), 5_000));
        })
        .catch(() => {
          // Best-effort: treat as unavailable.
          if (cancelled) return;
          void markThreadByComment(commentParam);
          showIds.push(window.setTimeout(() => setStaleToast(true), 0));
          showIds.push(window.setTimeout(() => setStaleToast(false), 5_000));
        });
    });
    return () => {
      cancelled = true;
      for (const id of showIds) window.clearTimeout(id);
    };
  }, [
    commentParam,
    fetched,
    anchor,
    markThreadRead,
    markThreadByComment,
    refreshDiscussions,
  ]);

  const shouldShowSkeleton = authLoading || (isAuthenticated && !fetched);

  const handleNewDiscussion = async (body: string) => {
    const discussion = await api.discussions.create(projectId, body);
    setDiscussions((prev) => [discussion, ...prev]);
  };

  const handleReply = async (discussionId: string, body: string) => {
    const reply = await api.discussions.reply(projectId, discussionId, body);
    setDiscussions((prev) =>
      prev.map((d) =>
        d.id === discussionId
          ? { ...d, replies: [...d.replies, reply] }
          : d
      )
    );
  };

  const handleEdit = async (discussionId: string, body: string) => {
    const updated = await api.discussions.update(projectId, discussionId, body);
    setDiscussions((prev) =>
      prev.map((d) => {
        if (d.id === discussionId) {
          return { ...d, body: updated.body, is_edited: updated.is_edited };
        }
        return {
          ...d,
          replies: d.replies.map((r) =>
            r.id === discussionId
              ? { ...r, body: updated.body, is_edited: updated.is_edited }
              : r
          ),
        };
      })
    );
  };

  const handleDelete = async (discussionId: string) => {
    await api.discussions.delete(projectId, discussionId);
    setDiscussions((prev) => {
      const filtered = prev.filter((d) => d.id !== discussionId);
      return filtered.map((d) => ({
        ...d,
        replies: d.replies.filter((r: Reply) => r.id !== discussionId),
      }));
    });
  };

  if (shouldShowSkeleton) {
    return (
      <div>
        <DiscussionsSkeleton />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div>
        <div className="bg-white rounded-xl border border-border p-8 text-center">
          <p className="text-muted-foreground text-sm mb-4">
            Sign up or log in to view and participate in discussions about this
            project.
          </p>
          <div className="flex justify-center gap-3">
            <Link href={buildLoginPath(`${pathname}#discussions`)} className="btn-primary">
              Log in
            </Link>
            <Link href={`/register?next=${encodeURIComponent(`${pathname}#discussions`)}`} className="btn-secondary">
              Sign up
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      {staleToast && (
        <div
          role="status"
          className="mb-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-4 py-3 text-sm"
        >
          This discussion is no longer available.
        </div>
      )}

      <NewDiscussionForm onSubmit={handleNewDiscussion} />

      <DiscussionList
        discussions={discussions}
        currentUserId={user?.id}
        onReply={handleReply}
        onEdit={handleEdit}
        onDelete={handleDelete}
        anchorCommentId={anchor ? commentParam : null}
      />
    </div>
  );
}
