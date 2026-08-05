"use client";

import { useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { Dialog } from "@/components/Dialog";
import { api } from "@/lib/api";
import type { Article } from "@/lib/api";
import { ArticleCardPreview } from "./ArticleCardPreview";

interface Props {
  article: Article;
  projectSlug: string;
  onClose: () => void;
  onSaved: (article: Article) => void;
}

export function ArticleCardPreviewDialog({
  article,
  projectSlug,
  onClose,
  onSaved,
}: Props) {
  const [summary, setSummary] = useState(article.summary);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setIsSaving(true);
    setError("");
    try {
      // "" is meaningful: it clears the override and returns the card to the
      // derived excerpt. The response carries a refreshed summary_display.
      const saved = await api.articles.update(projectSlug, article.id, {
        summary,
      });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save summary");
      setIsSaving(false);
    }
  };

  return (
    <Dialog isOpen onClose={onClose} className="max-w-2xl">
      <h2 className="text-lg font-semibold text-foreground">
        How this article will look in a list
      </h2>

      <div className="mt-4 max-h-[60vh] overflow-y-auto pr-1">
        <ArticleCardPreview
          article={article}
          summary={summary}
          onSummaryChange={setSummary}
        />
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <button
          onClick={onClose}
          disabled={isSaving}
          className="text-sm py-2 px-4 rounded-lg border border-border text-foreground hover:bg-muted transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary text-sm py-2 px-4"
        >
          {isSaving ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            "Save summary"
          )}
        </button>
      </div>
    </Dialog>
  );
}
