"use client";

import { useEffect, useState } from "react";
import { useAutoResize } from "@/hooks/useAutoResize";
import { Dialog } from "@/components/Dialog";

interface NewDiscussionModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (body: string) => Promise<void>;
  initialBody?: string;
  title?: string;
  submitLabel?: string;
}

export function NewDiscussionModal({
  open,
  onClose,
  onSubmit,
  initialBody = "",
  title = "Start a discussion",
  submitLabel = "Post",
}: NewDiscussionModalProps) {
  const [body, setBody] = useState(initialBody);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { ref: textareaRef, resize } = useAutoResize("24rem");

  useEffect(() => {
    if (open) {
      setBody(initialBody);
      setError("");
      setTimeout(() => {
        textareaRef.current?.focus();
        resize();
      }, 0);
    }
  }, [open, initialBody, textareaRef, resize]);

  const handleSubmit = async () => {
    if (!body.trim() || submitting) return;

    setSubmitting(true);
    setError("");
    try {
      await onSubmit(body.trim());
      setBody("");
      onClose();
    } catch {
      setError("Failed to post discussion. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) onClose();
  };

  return (
    <Dialog isOpen={open} onClose={handleClose} className="max-w-3xl" position="top">
      {/* Header */}
      <div className="flex items-center justify-between -mt-2 mb-3">
        <h2 className="text-base font-semibold text-foreground">
          {title}
        </h2>
        <button
          onClick={handleClose}
          disabled={submitting}
          className="text-muted-foreground hover:text-foreground transition-colors p-1 -mr-2"
          aria-label="Close"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M5 5l10 10M15 5L5 15" />
          </svg>
        </button>
      </div>

      {/* Content area */}
      <textarea
        ref={textareaRef}
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
          resize();
        }}
        placeholder="What's on your mind?"
        rows={4}
        className="w-full resize-none overflow-hidden border-none outline-none text-base leading-relaxed text-foreground placeholder:text-muted-foreground bg-transparent"
      />

      {error && (
        <p className="text-red-500 text-xs mb-2">{error}</p>
      )}

      {/* Separator + actions */}
      <div className="border-t border-border -mx-6 mb-4" />
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={handleSubmit}
          disabled={submitting || !body.trim()}
          className="btn-primary text-sm disabled:opacity-50"
        >
          {submitting ? "Saving..." : submitLabel}
        </button>
      </div>
    </Dialog>
  );
}
