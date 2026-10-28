"use client";

import { useTranslations } from "next-intl";
import { PhotoIcon } from "@heroicons/react/24/outline";
import type { CropRect } from "@/components/CroppedImage";
import { ArticleCover } from "./ArticleCover";

interface Props {
  // The cover, if the article has one, at a size fit for the slot.
  imageUrl: string | null;
  crop: CropRect | null;
  // Open the image dialog to pick and frame a cover.
  onPick: () => void;
  // Drop the cover. The card goes text-only with it.
  onRemove: () => void;
}

// Sits above the body in the editor, where the cover sits on the page. The
// control lives where its result appears.
export function CoverSlot({ imageUrl, crop, onPick, onRemove }: Props) {
  const t = useTranslations("articles.authoring.cover");

  if (imageUrl) {
    return (
      <div className="relative" data-testid="cover-slot">
        <ArticleCover src={imageUrl} crop={crop} priority />
        <div className="absolute top-2 right-2 flex gap-1.5">
          <button
            type="button"
            onClick={onPick}
            className="rounded-lg border border-border bg-white/95 px-2.5 py-1 text-xs font-medium text-foreground shadow-sm hover:bg-muted transition-colors"
          >
            {t("change")}
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="rounded-lg border border-border bg-white/95 px-2.5 py-1 text-xs font-medium text-muted-foreground shadow-sm hover:text-foreground hover:bg-muted transition-colors"
          >
            {t("remove")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      data-testid="cover-slot"
      onClick={onPick}
      className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border py-3 text-sm text-muted-foreground hover:border-accent hover:text-accent transition-colors"
    >
      <PhotoIcon className="w-4 h-4" />
      {t("add")}
    </button>
  );
}
