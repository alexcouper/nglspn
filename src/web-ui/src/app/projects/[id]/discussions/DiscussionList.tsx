"use client";

import { useState } from "react";
import { TrashIcon } from "@heroicons/react/24/outline";
import type { Discussion, Reply } from "@/lib/api";
import { ReplyForm } from "./ReplyForm";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function authorName(author: Discussion["author"]): string {
  if (!author) return "Deleted user";
  return [author.first_name, author.last_name].filter(Boolean).join(" ") || "Anonymous";
}

interface ReplyItemProps {
  reply: Reply;
  currentUserId?: string;
  onDelete: (id: string) => Promise<void>;
}

function ReplyItem({ reply, currentUserId, onDelete }: ReplyItemProps) {
  const [deleting, setDeleting] = useState(false);
  const isAuthor = currentUserId && reply.author?.id === currentUserId;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(reply.id);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="px-5 py-3 border-b border-border last:border-b-0">
      <div className="flex items-start justify-between gap-3 ml-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm mb-1">
            <span className="font-medium text-foreground">
              {authorName(reply.author)}
            </span>
            <span className="text-muted-foreground text-xs">
              {formatDate(reply.created_at)}
            </span>
          </div>
          <p className="text-foreground text-sm whitespace-pre-wrap">
            {reply.body}
          </p>
        </div>
        {isAuthor && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
            title="Delete"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

interface DiscussionItemProps {
  discussion: Discussion;
  currentUserId?: string;
  onReply: (discussionId: string, body: string) => Promise<void>;
  onDelete: (discussionId: string) => Promise<void>;
}

function DiscussionItem({
  discussion,
  currentUserId,
  onReply,
  onDelete,
}: DiscussionItemProps) {
  const [showReply, setShowReply] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const isAuthor = currentUserId && discussion.author?.id === currentUserId;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(discussion.id);
    } finally {
      setDeleting(false);
    }
  };

  const handleReply = async (body: string) => {
    await onReply(discussion.id, body);
    setShowReply(false);
  };

  return (
    <div className="bg-white rounded-xl border border-border overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-sm mb-2">
              <span className="font-medium text-foreground">
                {authorName(discussion.author)}
              </span>
              <span className="text-muted-foreground">
                {formatDate(discussion.created_at)}
              </span>
            </div>
            <p className="text-foreground text-sm whitespace-pre-wrap">
              {discussion.body}
            </p>
          </div>
          {isAuthor && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
              title="Delete"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="mt-3">
          <button
            onClick={() => setShowReply(!showReply)}
            className="text-xs text-muted-foreground hover:text-accent transition-colors"
          >
            Reply
          </button>
        </div>

        {showReply && (
          <div className="mt-3">
            <ReplyForm onSubmit={handleReply} onCancel={() => setShowReply(false)} />
          </div>
        )}
      </div>

      {discussion.replies.length > 0 && (
        <div className="border-t border-border bg-muted/50">
          {discussion.replies.map((reply) => (
            <ReplyItem
              key={reply.id}
              reply={reply}
              currentUserId={currentUserId}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface DiscussionListProps {
  discussions: Discussion[];
  currentUserId?: string;
  onReply: (discussionId: string, body: string) => Promise<void>;
  onDelete: (discussionId: string) => Promise<void>;
}

export function DiscussionList({
  discussions,
  currentUserId,
  onReply,
  onDelete,
}: DiscussionListProps) {
  if (discussions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 mt-6">
      {discussions.map((discussion) => (
        <DiscussionItem
          key={discussion.id}
          discussion={discussion}
          currentUserId={currentUserId}
          onReply={onReply}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
