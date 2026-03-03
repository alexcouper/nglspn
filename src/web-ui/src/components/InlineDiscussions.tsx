"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth";
import { api } from "@/lib/api";
import type { Discussion, Reply } from "@/lib/api";
import { DiscussionList } from "@/app/projects/[id]/discussions/DiscussionList";
import { NewDiscussionForm } from "@/app/projects/[id]/discussions/NewDiscussionForm";
import Link from "next/link";

interface InlineDiscussionsProps {
  projectId: string;
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
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [fetched, setFetched] = useState(false);
  const [error, setError] = useState("");

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
            <Link href="/login" className="btn-primary">
              Log in
            </Link>
            <Link href="/register" className="btn-secondary">
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

      <NewDiscussionForm onSubmit={handleNewDiscussion} />

      <DiscussionList
        discussions={discussions}
        currentUserId={user?.id}
        onReply={handleReply}
        onDelete={handleDelete}
      />
    </div>
  );
}
