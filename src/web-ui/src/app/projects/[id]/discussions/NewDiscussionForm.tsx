"use client";

import { useState } from "react";

interface NewDiscussionFormProps {
  onSubmit: (body: string) => Promise<void>;
}

export function NewDiscussionForm({ onSubmit }: NewDiscussionFormProps) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;

    setSubmitting(true);
    setError("");
    try {
      await onSubmit(body.trim());
      setBody("");
    } catch {
      setError("Failed to post discussion. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="bg-white rounded-xl border border-border p-4">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.shiftKey && !submitting && body.trim()) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Start a discussion..."
          rows={3}
          className="input w-full resize-none"
        />
        {error && (
          <p className="text-red-500 text-xs mt-1">{error}</p>
        )}
        <div className="flex items-center justify-end mt-3">
          {body.trim() && (
            <p className="text-xs text-muted-foreground mr-auto">
              <kbd className="font-medium">Shift + Enter</kbd> to send
            </p>
          )}
          <button
            type="submit"
            disabled={submitting || !body.trim()}
            className="btn-primary text-sm disabled:opacity-50"
          >
            {submitting ? "Posting..." : "Post"}
          </button>
        </div>
      </div>
    </form>
  );
}
