"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
  const { markThreadRead } = useNotifications();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const commentParam = searchParams.get("comment");
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [fetched, setFetched] = useState(false);
  const [error, setError] = useState("");
  const [staleToast, setStaleToast] = useState(false);
  const processedCommentRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated || authLoading) return;
    let cancelled = false;
    api.discussions
      .list(projectId)
      .then((data) => {
        if (!cancelled) setDiscussions(data);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load discussions");
      })
      .finally(() => {
        if (!cancelled) setFetched(true);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, isAuthenticated, authLoading]);

  // Resolve the comment param to {rootId, isRoot} once discussions are loaded.
  const anchor = useMemo(() => {
    if (!commentParam || !fetched) return null;
    return findCommentInTree(discussions, commentParam);
  }, [commentParam, fetched, discussions]);

  // Click-through side effects: highlight handled in children via anchorCommentId.
  // Here we mark-thread-read and surface "no longer available" toast as needed.
  useEffect(() => {
    if (!commentParam || !fetched) return;
    if (processedCommentRef.current === commentParam) return;
    processedCommentRef.current = commentParam;
    if (anchor) {
      void markThreadRead(anchor.rootId);
      return;
    }
    // Comment not present: show "no longer available" toast and best-effort
    // clear the notification.
    void markThreadRead(commentParam);
    const showId = window.setTimeout(() => setStaleToast(true), 0);
    const hideId = window.setTimeout(() => setStaleToast(false), 5_000);
    return () => {
      window.clearTimeout(showId);
      window.clearTimeout(hideId);
    };
  }, [commentParam, fetched, anchor, markThreadRead]);

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
