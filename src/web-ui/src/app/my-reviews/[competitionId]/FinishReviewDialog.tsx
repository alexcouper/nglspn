"use client";

interface FinishReviewDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isFinishing?: boolean;
}

export function FinishReviewDialog({
  isOpen,
  onConfirm,
  onCancel,
  isFinishing = false,
}: FinishReviewDialogProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      <div className="relative bg-white rounded-xl shadow-lg border border-border max-w-md w-full mx-4 p-6">
        <h2 className="text-base font-semibold text-foreground mb-3">
          Finish review?
        </h2>

        <p className="text-sm text-muted-foreground mb-5">
          This will lock your rankings. You won&apos;t be able to make changes.
        </p>

        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isFinishing}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isFinishing}
            className="btn-primary"
          >
            {isFinishing ? "Finishing..." : "Finish Review"}
          </button>
        </div>
      </div>
    </div>
  );
}
