"use client";

import type { CropRect } from "@/components/CroppedImage";
import { CroppedImage } from "@/components/CroppedImage";
import type { Article, ProjectImage } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import { ArticleCardPreview } from "./ArticleCardPreview";
import type { ListingImageMode } from "@/lib/api";

const SUMMARY_MAX = 300;

// What the author actually chose, in words. `auto` is a default they never
// made, so saying so is the difference between "we picked this" and "you did".
const MODE_LABEL: Record<ListingImageMode, string> = {
  auto: "Following the first image in this article.",
  chosen: "Your choice.",
  none: "This article shows no image in listings.",
};

interface Props {
  article: Article;
  summary: string;
  listingImage: ProjectImage | null;
  crop: CropRect | null;
  mode: ListingImageMode;
  onSummaryChange: (value: string) => void;
  onChangeImage: () => void;
  onRemoveImage: () => void;
}

export function ListingSettingsPanel({
  article,
  summary,
  listingImage,
  crop,
  mode,
  onSummaryChange,
  onChangeImage,
  onRemoveImage,
}: Props) {
  const imageUrl = listingImage
    ? (pickVariant(listingImage.variants, "medium") ?? listingImage.url)
    : null;

  return (
    <div className="space-y-6">
      <div>
        <label
          htmlFor="article-summary"
          className="block text-sm font-medium text-foreground"
        >
          Summary
        </label>
        <textarea
          id="article-summary"
          value={summary}
          placeholder={article.summary_display}
          maxLength={SUMMARY_MAX}
          rows={3}
          onChange={(e) => onSummaryChange(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
        />
        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
          <span>Leave empty to use the start of the article.</span>
          <span>
            {summary.length}/{SUMMARY_MAX}
          </span>
        </div>
      </div>

      <div>
        <span className="block text-sm font-medium text-foreground">Image</span>
        <div className="mt-2 flex items-start gap-4">
          <div className="w-40 shrink-0 overflow-hidden rounded-lg border border-border">
            {imageUrl ? (
              <CroppedImage
                src={imageUrl}
                alt={listingImage?.original_filename ?? ""}
                crop={crop}
                priority
                testId="listing-image-thumb"
              />
            ) : (
              <div className="flex aspect-[16/9] items-center justify-center text-xs text-muted-foreground">
                No image
              </div>
            )}
          </div>
          <div className="min-w-0 space-y-2 text-sm">
            <p className="text-muted-foreground">{MODE_LABEL[mode]}</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={onChangeImage}
                className="rounded-lg border border-border px-3 py-1.5 text-foreground hover:bg-muted transition-colors"
              >
                {listingImage ? "Change…" : "Choose an image…"}
              </button>
              {mode !== "none" && (
                <button
                  onClick={onRemoveImage}
                  className="rounded-lg px-3 py-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <ArticleCardPreview
        article={article}
        summary={summary}
        imageUrl={imageUrl}
        crop={crop}
      />
    </div>
  );
}
