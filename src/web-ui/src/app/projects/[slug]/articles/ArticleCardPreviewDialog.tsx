"use client";

import { useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { Dialog } from "@/components/Dialog";
import { ImageCropDialog } from "@/components/ImageCropDialog";
import type { CropRect } from "@/components/CroppedImage";
import { api } from "@/lib/api";
import type { Article } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import { ArticleCardPreview } from "./ArticleCardPreview";

// Listing cards are always 16:9 so a grid of them stays uniform. Mirrors
// CARD_RATIO in services/articles/crop.py.
const CARD_RATIO = 16 / 9;

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
  const [cardCrop, setCardCrop] = useState<CropRect | null>(article.card_crop);
  const [isCropping, setIsCropping] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const hero = article.hero_image;

  const handleSave = async () => {
    setIsSaving(true);
    setError("");
    try {
      // "" and null are both meaningful: they clear the respective override and
      // return the card to the derived excerpt and the hero-derived framing.
      // The response carries refreshed summary_display and card_crop_display.
      const saved = await api.articles.update(projectSlug, article.id, {
        summary,
        card_crop: cardCrop,
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
          cardCrop={cardCrop}
          onSummaryChange={setSummary}
          onAdjustFraming={() => setIsCropping(true)}
          onResetFraming={() => setCardCrop(null)}
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
            "Save"
          )}
        </button>
      </div>

      {isCropping && hero?.width && hero?.height && (
        <ImageCropDialog
          isOpen
          src={pickVariant(hero.variants, "large") ?? hero.url}
          naturalWidth={hero.width}
          naturalHeight={hero.height}
          // Falls back to the derived rect so re-framing starts from what the
          // card currently shows rather than jumping to the middle.
          initial={cardCrop ?? article.card_crop_display}
          lockRatio={CARD_RATIO}
          title="Frame the listing card"
          onConfirm={(crop) => {
            setCardCrop(crop);
            setIsCropping(false);
          }}
          onCancel={() => setIsCropping(false)}
        />
      )}
    </Dialog>
  );
}
