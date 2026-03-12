"use client";

import { useEffect, useRef, useState } from "react";
import { useAutoResize } from "@/hooks/useAutoResize";

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
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setBody(initialBody);
      setError("");
      document.body.style.overflow = "hidden";
      setTimeout(() => {
        textareaRef.current?.focus();
        resize();
      }, 0);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open, initialBody, textareaRef, resize]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open && !submitting) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, submitting, onClose]);

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

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]"
      onClick={(e) => {
        if (e.target === overlayRef.current && !submitting) onClose();
      }}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-3xl bg-white rounded-xl shadow-xl animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <h2 className="text-base font-semibold text-foreground">
            {title}
          </h2>
          <button
            onClick={onClose}
            disabled={submitting}
            className="text-muted-foreground hover:text-foreground transition-colors p-1 -mr-1"
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

        {/* Content area — feels like paper */}
        <div className="px-6 pb-2">
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
        </div>

        {error && (
          <p className="text-red-500 text-xs px-6 pb-2">{error}</p>
        )}

        {/* Separator + actions */}
        <div className="border-t border-border mx-6" />
        <div className="flex items-center justify-end gap-2 px-6 py-4">
          <button
            onClick={handleSubmit}
            disabled={submitting || !body.trim()}
            className="btn-primary text-sm disabled:opacity-50"
          >
            {submitting ? "Saving..." : submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
