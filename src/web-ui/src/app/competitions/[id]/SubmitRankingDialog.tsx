"use client";

import { useTranslations } from "next-intl";
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
  const t = useTranslations("competitions.submitRankingDialog");
  const tc = useTranslations("common.actions");
  const isEmpty = rankedCount === 0;

  return (
    <Dialog isOpen={isOpen} onClose={onCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        {isEmpty ? t("titleEmpty") : t("title")}
      </h2>

      <p className="text-sm text-muted-foreground mb-5" data-testid="submit-dialog-body">
        {isEmpty ? t("bodyEmpty") : t("body")}
      </p>

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="btn-secondary"
        >
          {tc("cancel")}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
          data-testid="confirm-submit"
          className="btn-primary"
        >
          {isSubmitting
            ? t("submitting")
            : isEmpty
              ? t("submitEmpty")
              : t("submit")}
        </button>
      </div>
    </Dialog>
  );
}
