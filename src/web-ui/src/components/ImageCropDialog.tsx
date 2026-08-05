"use client";

import { useState } from "react";
import { Dialog } from "./Dialog";
import { ImageCropper, defaultCrop } from "./ImageCropper";
import type { CropRect } from "./CroppedImage";

interface Props {
  isOpen: boolean;
  src: string;
  naturalWidth: number;
  naturalHeight: number;
  initial?: CropRect | null;
  // Fixes the box's shape and removes its handles. 16/9 for listing cards.
  lockRatio?: number;
  title?: string;
  hint?: string;
  confirmLabel?: string;
  onConfirm: (crop: CropRect) => void;
  onCancel: () => void;
}

// A dialog around ImageCropper and nothing else: the cropper owns all the
// geometry, so anywhere else that needs one can drop it into a panel, a step in
// a wizard, or a page without unpicking a modal.
//
// Callers mount this only while it is open, so the working crop resets by
// remounting rather than by an effect watching `isOpen`.
export function ImageCropDialog({
  isOpen,
  src,
  naturalWidth,
  naturalHeight,
  initial,
  lockRatio,
  title = "Choose the framing",
  hint,
  confirmLabel = "Use it",
  onConfirm,
  onCancel,
}: Props) {
  const [crop, setCrop] = useState<CropRect>(
    () =>
      initial ??
      defaultCrop({
        width: naturalWidth,
        height: naturalHeight,
        lockRatio,
        minRatio: 1,
        maxRatio: 4,
      }),
  );

  const defaultHint = lockRatio
    ? "Drag to move the image, and zoom to change how much of it is used."
    : "Drag to move the image. Drag the top or bottom edge to change the shape.";

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onCancel}
      // Full-screen under `sm`: a crop stage inside a padded modal on a 375px
      // screen leaves nothing to aim at. The column layout keeps the buttons
      // pinned — a near-square box is tall enough to push them off the bottom
      // of the viewport otherwise.
      className="max-w-3xl max-h-[calc(100vh-4rem)] flex flex-col max-sm:rounded-none max-sm:max-h-screen max-sm:min-h-screen"
    >
      <h2 className="shrink-0 text-lg font-semibold text-foreground">{title}</h2>
      <p className="mt-1 shrink-0 text-sm text-muted-foreground">
        {hint ?? defaultHint}
      </p>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto">
        <ImageCropper
          src={src}
          naturalWidth={naturalWidth}
          naturalHeight={naturalHeight}
          value={crop}
          onChange={setCrop}
          lockRatio={lockRatio}
        />
      </div>

      <div className="mt-5 flex shrink-0 justify-end gap-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
        <button
          onClick={() => onConfirm(crop)}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent/90"
        >
          {confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}
