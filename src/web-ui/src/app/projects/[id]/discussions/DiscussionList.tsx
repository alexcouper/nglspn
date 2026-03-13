"use client";

import { useState } from "react";
import { PencilIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAutoResize } from "@/hooks/useAutoResize";
import type { Discussion, Reply } from "@/lib/api";
import { ReplyForm } from "./ReplyForm";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
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
}

function ReplyItem({ reply, currentUserId, onEdit, onDelete }: ReplyItemProps) {
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
            <p className="text-foreground text-sm whitespace-pre-wrap">
              {reply.body}
            </p>
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
}

function DiscussionItem({
  discussion,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
}: DiscussionItemProps) {
  const [showReply, setShowReply] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(discussion.body);
  const [saving, setSaving] = useState(false);
  const { ref: editRef, resize: editResize } = useAutoResize();
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

  const handleSaveEdit = async () => {
    if (!editBody.trim()) return;
    setSaving(true);
    try {
      await onEdit(discussion.id, editBody.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditBody(discussion.body);
    setEditing(false);
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
              {discussion.is_edited && (
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
                  rows={3}
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
              <p className="text-foreground text-sm whitespace-pre-wrap">
                {discussion.body}
              </p>
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

        {!editing && (
          <div className="mt-3">
            <button
              onClick={() => setShowReply(!showReply)}
              className="text-xs text-muted-foreground hover:text-accent transition-colors"
            >
              Reply
            </button>
          </div>
        )}

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
              onEdit={onEdit}
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
  onEdit: (discussionId: string, body: string) => Promise<void>;
  onDelete: (discussionId: string) => Promise<void>;
}

export function DiscussionList({
  discussions,
  currentUserId,
  onReply,
  onEdit,
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
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
