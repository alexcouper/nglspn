"use client";

import { useTranslations } from "next-intl";
import { Translatable } from "@/components/Translatable";

interface PublishDialogProps {
  isOpen: boolean;
  missing: string[];
  onClose: () => void;
}

export function PublishDialog({ isOpen, missing, onClose }: PublishDialogProps) {
  const t = useTranslations();

  const FIELD_KEYS: Record<string, string> = {
    title: "projects.publishDialog.fieldTitle",
    description: "projects.publishDialog.fieldDescription",
    main_image: "projects.publishDialog.fieldMainImage",
  };

  if (!isOpen) return null;

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
        <h2 className="text-lg font-semibold text-foreground">
          <Translatable tKey="projects.publishDialog.heading">{t("projects.publishDialog.heading")}</Translatable>
        </h2>
        <p className="text-sm text-muted-foreground mt-2">
          <Translatable tKey="projects.publishDialog.message">{t("projects.publishDialog.message")}</Translatable>
        </p>
        <ul className="mt-3 space-y-1 text-sm text-foreground list-disc list-inside">
          {missing.map((field) => {
            const tKey = FIELD_KEYS[field];
            return (
              <li key={field}>
                {tKey ? <Translatable tKey={tKey}>{t(tKey)}</Translatable> : field}
              </li>
            );
          })}
        </ul>
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="btn-primary text-sm py-2 px-4"
          >
            <Translatable tKey="common.close">{t("common.close")}</Translatable>
          </button>
        </div>
      </div>
    </div>
  );
}
