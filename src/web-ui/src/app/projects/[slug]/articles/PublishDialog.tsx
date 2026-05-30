"use client";

import { ArrowPathIcon } from "@heroicons/react/24/outline";

interface Props {
  isPublishing: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function PublishDialog({ isPublishing, onClose, onConfirm }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-foreground">Publish article</h2>
        <p className="text-sm text-muted-foreground mt-2">
          Publishing makes the article visible to everyone on the project page.
        </p>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isPublishing}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPublishing}
            className="btn-primary text-sm py-2 px-4"
          >
            {isPublishing ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              "Publish"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
