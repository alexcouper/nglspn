"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Dialog } from "@/components/Dialog";

interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  projectTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export function DeleteConfirmationDialog({
  isOpen,
  projectTitle,
  onConfirm,
  onCancel,
  isDeleting = false,
}: DeleteConfirmationDialogProps) {
  const t = useTranslations("my-projects.deleteDialog");
  const tc = useTranslations("common.actions");
  const [confirmText, setConfirmText] = useState("");

  const handleCancel = () => {
    setConfirmText("");
    onCancel();
  };

  // The word the owner has to type is part of the copy, so it comes from the
  // messages too — the check must match what the dialog asks for.
  const confirmWord = t("confirmWord");
  const canDelete = confirmText.toLowerCase() === confirmWord;

  return (
    <Dialog isOpen={isOpen} onClose={handleCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        {t("title")}
      </h2>

      <p className="text-sm text-muted-foreground mb-4">
        {t.rich("warning", {
          title: projectTitle,
          strong: (chunks) => <strong className="text-foreground">{chunks}</strong>,
        })}
      </p>

      <p className="text-xs text-muted-foreground mb-3">
        {t.rich("typeToConfirm", {
          word: confirmWord,
          strong: (chunks) => <strong className="text-red-600">{chunks}</strong>,
        })}
      </p>

      <input
        type="text"
        value={confirmText}
        onChange={(e) => setConfirmText(e.target.value)}
        className="input mb-5"
        placeholder={t("placeholder", { word: confirmWord })}
        autoFocus
        disabled={isDeleting}
      />

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isDeleting}
          className="btn-secondary"
        >
          {tc("cancel")}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={!canDelete || isDeleting}
          className="btn-primary bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isDeleting ? tc("deleting") : t("confirm")}
        </button>
      </div>
    </Dialog>
  );
}
