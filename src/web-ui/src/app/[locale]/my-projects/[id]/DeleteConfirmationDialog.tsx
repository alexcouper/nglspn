"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Dialog } from "@/components/Dialog";
import { Translatable } from "@/components/Translatable";

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
  const t = useTranslations();
  const [confirmText, setConfirmText] = useState("");

  const handleCancel = () => {
    setConfirmText("");
    onCancel();
  };

  const canDelete = confirmText.toLowerCase() === t("projects.deleteDialog.confirmText").toLowerCase();

  return (
    <Dialog isOpen={isOpen} onClose={handleCancel}>
      <h2 className="text-base font-semibold text-foreground mb-3">
        <Translatable tKey="projects.deleteDialog.heading">{t("projects.deleteDialog.heading")}</Translatable>
      </h2>

      <p className="text-sm text-muted-foreground mb-4">
        <Translatable tKey="projects.deleteDialog.confirmation">
          {t("projects.deleteDialog.confirmation", { title: projectTitle })}
        </Translatable>
      </p>

      <p className="text-xs text-muted-foreground mb-3">
        <Translatable tKey="projects.deleteDialog.instruction">
          {t("projects.deleteDialog.instruction")}
        </Translatable>
      </p>

      <input
        type="text"
        value={confirmText}
        onChange={(e) => setConfirmText(e.target.value)}
        className="input mb-5"
        placeholder={t("projects.deleteDialog.placeholder")}
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
          <Translatable tKey="common.cancel">{t("common.cancel")}</Translatable>
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={!canDelete || isDeleting}
          className="btn-primary bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isDeleting ? (
            <Translatable tKey="projects.deleteDialog.deleting">{t("projects.deleteDialog.deleting")}</Translatable>
          ) : (
            <Translatable tKey="projects.deleteDialog.deleteButton">{t("projects.deleteDialog.deleteButton")}</Translatable>
          )}
        </button>
      </div>
    </Dialog>
  );
}
