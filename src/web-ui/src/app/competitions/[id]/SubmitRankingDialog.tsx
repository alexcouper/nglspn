"use client";

import { Dialog } from "@/components/Dialog";

interface SubmitRankingDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function SubmitRankingDialog({
  isOpen,
  onConfirm,
  onCancel,
  isSubmitting = false,
}: SubmitRankingDialogProps) {
  return (
    <Dialog isOpen={isOpen} onClose={onCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        Submit your ranking?
      </h2>

      <p className="text-sm text-muted-foreground mb-5">
        Your ranking will be locked in. You can reopen it later if voting is
        still open.
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
          className="btn-primary"
        >
          {isSubmitting ? "Submitting..." : "Submit Ranking"}
        </button>
      </div>
    </Dialog>
  );
}
