"use client";

import { Dialog } from "@/components/Dialog";

interface SubmitRankingDialogProps {
  isOpen: boolean;
  rankedCount: number;
  onConfirm: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function SubmitRankingDialog({
  isOpen,
  rankedCount,
  onConfirm,
  onCancel,
  isSubmitting = false,
}: SubmitRankingDialogProps) {
  const isEmpty = rankedCount === 0;

  return (
    <Dialog isOpen={isOpen} onClose={onCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        {isEmpty ? "Submit without ranking anything?" : "Submit your ranking?"}
      </h2>

      <p className="text-sm text-muted-foreground mb-5" data-testid="submit-dialog-body">
        {isEmpty
          ? "You have not ranked any projects, so none will be counted as your preference. You can reopen your review later if voting is still open."
          : "Your ranking will be locked in. You can reopen it later if voting is still open."}
      </p>

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="btn-secondary"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
          data-testid="confirm-submit"
          className="btn-primary"
        >
          {isSubmitting
            ? "Submitting..."
            : isEmpty
              ? "Submit empty ballot"
              : "Submit Ranking"}
        </button>
      </div>
    </Dialog>
  );
}
