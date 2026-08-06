"use client";

import { useRef, useState } from "react";
import { ArrowPathIcon, PhotoIcon } from "@heroicons/react/24/outline";
import { Dialog } from "@/components/Dialog";
import { ImageCropper, defaultCrop } from "@/components/ImageCropper";
import type { CropRect } from "@/components/CroppedImage";
import { useImageUpload } from "@/hooks/useImageUpload";
import { api } from "@/lib/api";
import type { ProjectImage } from "@/lib/api";
import { pickVariant } from "@/lib/utils";

// Listing cards are always 16:9 so a grid of them stays uniform. Mirrors
// CARD_RATIO in services/articles/crop.py.
const CARD_RATIO = 16 / 9;

interface Props {
  // Slug or id — whatever the article editor addresses the project by. Article
  // images hang off the article's own endpoints, so this is the same reference
  // the rest of the editor uses.
  projectRef: string;
  articleId: string;
  // Every image uploaded for this article, from the image-article link. Not
  // parsed out of the body, so an image the author uploaded here is offered on
  // the same footing as one they inserted into the article.
  images: ProjectImage[];
  currentImageId: string | null;
  currentCrop: CropRect | null;
  onConfirm: (image: ProjectImage, crop: CropRect) => void;
  onRemove: () => void;
  onClose: () => void;
}

// Two steps: pick an image, then frame it at 16:9. Step two hosts ImageCropper
// directly rather than nesting an ImageCropDialog inside this one.
export function ListingImageDialog({
  projectRef,
  articleId,
  images,
  currentImageId,
  currentCrop,
  onConfirm,
  onRemove,
  onClose,
}: Props) {
  const [selected, setSelected] = useState<ProjectImage | null>(
    () => images.find((image) => image.id === currentImageId) ?? null,
  );
  const [step, setStep] = useState<"pick" | "frame">("pick");
  const [crop, setCrop] = useState<CropRect | null>(null);
  const [error, setError] = useState("");
  // An upload the article has not adopted yet. Cancelling deletes it, so a
  // change of mind does not leave a file behind.
  const [pendingUpload, setPendingUpload] = useState<ProjectImage | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { uploadFile, isUploading } = useImageUpload({
    target: { kind: "article", projectRef, articleId },
    onUploadComplete: (image) => {
      setPendingUpload(image);
      // A fresh upload has nothing to choose between, so it continues straight
      // to framing.
      openFraming(image);
    },
    onError: (err) => setError(err.message),
  });

  // A rectangle drawn on one image means nothing on another, so only the image
  // that is already chosen reopens on its stored crop.
  function openFraming(image: ProjectImage) {
    setSelected(image);
    setCrop(image.id === currentImageId ? currentCrop : null);
    setStep("frame");
  }

  function discardPendingUpload() {
    if (!pendingUpload) return;
    // Best-effort: article images are excluded from the project gallery, so a
    // failure leaves an invisible orphan rather than a visible one.
    api.articles.deleteImage(projectRef, articleId, pendingUpload.id).catch(() => {});
    setPendingUpload(null);
  }

  function handleCancel() {
    discardPendingUpload();
    onClose();
  }

  return (
    <Dialog
      isOpen
      onClose={handleCancel}
      // Full-screen under `sm`: a crop stage inside a padded modal on a 375px
      // screen leaves nothing to aim at.
      className="max-w-3xl max-h-[calc(100vh-4rem)] flex flex-col max-sm:rounded-none max-sm:max-h-screen max-sm:min-h-screen"
    >
      <h2 className="shrink-0 text-lg font-semibold text-foreground">
        {step === "pick" ? "Choose a listing image" : "Frame the card"}
      </h2>
      <p className="mt-1 shrink-0 text-sm text-muted-foreground">
        {step === "pick"
          ? "Pick one of this article's images, or upload a new one."
          : "Drag to move the image, and zoom to change how much of it is used."}
      </p>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto">
        {step === "pick" ? (
          <PickStep
            images={pendingUpload ? [...images, pendingUpload] : images}
            selectedId={selected?.id ?? null}
            isUploading={isUploading}
            inputRef={inputRef}
            onSelect={setSelected}
            onFile={uploadFile}
          />
        ) : (
          selected?.width &&
          selected?.height && (
            <ImageCropper
              src={pickVariant(selected.variants, "large") ?? selected.url}
              naturalWidth={selected.width}
              naturalHeight={selected.height}
              value={crop}
              onChange={setCrop}
              lockRatio={CARD_RATIO}
              previewLabel="Card"
            />
          )
        )}
      </div>

      {error && (
        <p className="mt-3 shrink-0 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="mt-5 flex shrink-0 items-center justify-between gap-2">
        {step === "pick" ? (
          <button
            onClick={() => {
              discardPendingUpload();
              onRemove();
            }}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            Remove image
          </button>
        ) : (
          <button
            onClick={() => setStep("pick")}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            Back
          </button>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          {step === "pick" ? (
            <button
              onClick={() => selected && openFraming(selected)}
              disabled={!selected}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
            >
              Next
            </button>
          ) : (
            <button
              onClick={() => {
                if (!selected) return;
                onConfirm(
                  selected,
                  crop ??
                    defaultCrop({
                      width: selected.width!,
                      height: selected.height!,
                      lockRatio: CARD_RATIO,
                    }),
                );
              }}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent/90"
            >
              Use it
            </button>
          )}
        </div>
      </div>
    </Dialog>
  );
}

function PickStep({
  images,
  selectedId,
  isUploading,
  inputRef,
  onSelect,
  onFile,
}: {
  images: ProjectImage[];
  selectedId: string | null;
  isUploading: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onSelect: (image: ProjectImage) => void;
  onFile: (file: File) => void;
}) {
  // Without recorded dimensions there is nothing to frame, so those images are
  // not offered.
  const selectable = images.filter((image) => image.width && image.height);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {/* Outside the upload button: a file input nested in a button is
          interactive content inside interactive content. */}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
      {selectable.map((image) => (
        <button
          key={image.id}
          onClick={() => onSelect(image)}
          aria-pressed={image.id === selectedId}
          title={image.original_filename}
          className={`relative aspect-[16/9] overflow-hidden rounded-lg border-2 transition-colors ${
            image.id === selectedId
              ? "border-accent"
              : "border-border hover:border-foreground/30"
          }`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={pickVariant(image.variants, "thumb") ?? image.url}
            alt={image.original_filename}
            className="h-full w-full object-cover"
          />
        </button>
      ))}

      <button
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="flex aspect-[16/9] flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-border text-muted-foreground hover:border-foreground/30 disabled:opacity-50"
      >
        {isUploading ? (
          <ArrowPathIcon className="h-6 w-6 animate-spin" />
        ) : (
          <PhotoIcon className="h-6 w-6" />
        )}
        <span className="text-sm">
          {isUploading ? "Uploading…" : "Upload new"}
        </span>
      </button>
    </div>
  );
}
