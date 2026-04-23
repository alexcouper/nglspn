"use client";

import { useTranslations } from "next-intl";
import { Dialog } from "@/components/Dialog";
import { Translatable } from "@/components/Translatable";

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
  const t = useTranslations();
  return (
    <Dialog isOpen={isOpen} onClose={onCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        <Translatable tKey="reviews.finishDialog.heading">{t("reviews.finishDialog.heading")}</Translatable>
      </h2>

      <p className="text-sm text-muted-foreground mb-5">
        <Translatable tKey="reviews.finishDialog.confirmation">{t("reviews.finishDialog.confirmation")}</Translatable>
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
          {isFinishing ? (
            <Translatable tKey="reviews.finishDialog.finishing">{t("reviews.finishDialog.finishing")}</Translatable>
          ) : (
            <Translatable tKey="reviews.finishDialog.finishButton">{t("reviews.finishDialog.finishButton")}</Translatable>
          )}
        </button>
      </div>
    </Dialog>
  );
}
