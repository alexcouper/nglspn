"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { PencilIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAutoResize } from "@/hooks/useAutoResize";
import type { Discussion, Reply } from "@/lib/api";
import { NewDiscussionModal } from "@/components/NewDiscussionModal";
import { ReplyForm } from "./ReplyForm";

const HIGHLIGHT_CLASSES =
  "ring-2 ring-amber-300/80 ring-offset-1 transition-shadow duration-700";

function fullDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function relativeDate(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const seconds = Math.floor((now - then) / 1000);

  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo`;
  const years = Math.floor(days / 365);
  return `${years}y`;
}

function authorName(author: Discussion["author"]): string {
  if (!author) return "Deleted user";
  return [author.first_name, author.last_name].filter(Boolean).join(" ") || "Anonymous";
}

interface ReplyItemProps {
  reply: Reply;
  currentUserId?: string;
  onEdit: (id: string, body: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onReplyClick: () => void;
  isAnchor?: boolean;
}

function ReplyItem({
  reply,
  currentUserId,
  onEdit,
  onDelete,
  onReplyClick,
  isAnchor,
}: ReplyItemProps) {
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(reply.body);
  const [saving, setSaving] = useState(false);
  const { ref: editRef, resize: editResize } = useAutoResize();
  const isAuthor = currentUserId && reply.author?.id === currentUserId;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(reply.id);
    } finally {
      setDeleting(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editBody.trim()) return;
    setSaving(true);
    try {
      await onEdit(reply.id, editBody.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditBody(reply.body);
    setEditing(false);
  };

  const itemRef = useRef<HTMLDivElement>(null);
  const [highlighted, setHighlighted] = useState(false);
  useEffect(() => {
    if (!isAnchor) return;
    itemRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlighted(true);
    const t = window.setTimeout(() => setHighlighted(false), 2_000);
    return () => window.clearTimeout(t);
  }, [isAnchor]);

  return (
    <div
      ref={itemRef}
      id={`comment-${reply.id}`}
      className={`px-5 py-3 border-b border-border last:border-b-0 ${
        highlighted ? HIGHLIGHT_CLASSES : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3 ml-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm mb-1">
            <span className="font-medium text-foreground">
              {authorName(reply.author)}
            </span>
            <span className="text-muted-foreground text-xs" title={fullDate(reply.created_at)}>
              {relativeDate(reply.created_at)}
            </span>
            {reply.is_edited && (
              <span className="text-muted-foreground text-xs">(edited)</span>
            )}
          </div>
          {editing ? (
            <div className="space-y-2">
              <textarea
                ref={editRef}
                value={editBody}
                onChange={(e) => {
                  setEditBody(e.target.value);
                  editResize();
                }}
                rows={2}
                className="input w-full resize-none overflow-hidden text-sm"
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSaveEdit}
                  disabled={saving || !editBody.trim()}
                  className="btn-primary text-xs disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-foreground text-base whitespace-pre-wrap">
                {reply.body}
              </p>
              <button
                onClick={onReplyClick}
                className="text-xs text-muted-foreground hover:text-accent transition-colors mt-1"
              >
                Reply
              </button>
            </>
          )}
        </div>
        {isAuthor && !editing && (
          <div className="flex gap-1">
            <button
              onClick={() => setEditing(true)}
              className="p-1.5 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
              title="Edit"
            >
              <PencilIcon className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
              title="Delete"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface DiscussionItemProps {
  discussion: Discussion;
  currentUserId?: string;
  onReply: (discussionId: string, body: string) => Promise<void>;
  onEdit: (discussionId: string, body: string) => Promise<void>;
  onDelete: (discussionId: string) => Promise<void>;
  anchorCommentId?: string | null;
}

function DiscussionItem({
  discussion,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
  anchorCommentId,
}: DiscussionItemProps) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [rootHighlighted, setRootHighlighted] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const isAuthor = currentUserId && discussion.author?.id === currentUserId;
  const matchesRoot = anchorCommentId === discussion.id;
  const anchoredReply = anchorCommentId
    ? discussion.replies.find((r) => r.id === anchorCommentId)
    : undefined;

  useEffect(() => {
    if (!matchesRoot && !anchoredReply) return;
    setReplyingTo(matchesRoot ? discussion.id : anchoredReply!.id);
    if (matchesRoot) {
      rootRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      setRootHighlighted(true);
      const t = window.setTimeout(() => setRootHighlighted(false), 2_000);
      return () => window.clearTimeout(t);
    }
  }, [matchesRoot, anchoredReply, discussion.id]);

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
    setReplyingTo(null);
  };

  const toggleReplyingTo = (id: string) =>
    setReplyingTo((prev) => (prev === id ? null : id));

  const handleSaveEdit = async (body: string) => {
    await onEdit(discussion.id, body);
    setEditing(false);
  };

  return (
    <div
      ref={rootRef}
      id={`comment-${discussion.id}`}
      className={`bg-white rounded-xl border border-border overflow-hidden ${
        rootHighlighted ? HIGHLIGHT_CLASSES : ""
      }`}
    >
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-sm mb-2">
              <span className="font-medium text-foreground">
                {authorName(discussion.author)}
              </span>
              <span className="text-muted-foreground text-xs" title={fullDate(discussion.created_at)}>
                {relativeDate(discussion.created_at)}
              </span>
              {discussion.is_edited && (
                <span className="text-muted-foreground text-xs">(edited)</span>
              )}
            </div>
            <p className="text-foreground text-base whitespace-pre-wrap">
              {discussion.body}
            </p>
          </div>
          {isAuthor && (
            <div className="flex gap-1">
              <button
                onClick={() => setEditing(true)}
                className="p-1.5 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
                title="Edit"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
                title="Delete"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        <div className="mt-3">
          <button
            onClick={() => toggleReplyingTo(discussion.id)}
            className="text-xs text-muted-foreground hover:text-accent transition-colors"
          >
            Reply
          </button>
        </div>

        {replyingTo === discussion.id && (
          <div className="mt-3">
            <ReplyForm onSubmit={handleReply} onCancel={() => setReplyingTo(null)} />
          </div>
        )}
      </div>

      {discussion.replies.length > 0 && (
        <div className="border-t border-border bg-muted/50">
          {discussion.replies.map((reply) => (
            <Fragment key={reply.id}>
              <ReplyItem
                reply={reply}
                currentUserId={currentUserId}
                onEdit={onEdit}
                onDelete={onDelete}
                onReplyClick={() => toggleReplyingTo(reply.id)}
                isAnchor={anchorCommentId === reply.id}
              />
              {replyingTo === reply.id && (
                <div className="px-5 py-3 border-b border-border last:border-b-0 bg-muted/30">
                  <ReplyForm
                    onSubmit={handleReply}
                    onCancel={() => setReplyingTo(null)}
                  />
                </div>
              )}
            </Fragment>
          ))}
        </div>
      )}

      <NewDiscussionModal
        open={editing}
        onClose={() => setEditing(false)}
        onSubmit={handleSaveEdit}
        initialBody={discussion.body}
        title="Edit discussion"
        submitLabel="Save"
      />
    </div>
  );
}

interface DiscussionListProps {
  discussions: Discussion[];
  currentUserId?: string;
  onReply: (discussionId: string, body: string) => Promise<void>;
  onEdit: (discussionId: string, body: string) => Promise<void>;
  onDelete: (discussionId: string) => Promise<void>;
  anchorCommentId?: string | null;
}

export function DiscussionList({
  discussions,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
  anchorCommentId,
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
          onEdit={onEdit}
          onDelete={onDelete}
          anchorCommentId={anchorCommentId}
        />
      ))}
    </div>
  );
}
