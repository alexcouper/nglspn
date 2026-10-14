"use client";

import { useTranslations } from "next-intl";

const FIELD_KEYS: Record<string, "title" | "description" | "mainImage"> = {
  title: "title",
  description: "description",
  main_image: "mainImage",
};

interface PublishDialogProps {
  isOpen: boolean;
  missing: string[];
  onClose: () => void;
}

export function PublishDialog({ isOpen, missing, onClose }: PublishDialogProps) {
  const t = useTranslations("my-projects.publishDialog");
  const tc = useTranslations("common.actions");
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
          {t("title")}
        </h2>
        <p className="text-sm text-muted-foreground mt-2">
          {t("intro")}
        </p>
        <ul className="mt-3 space-y-1 text-sm text-foreground list-disc list-inside">
          {missing.map((field) => {
            const key = FIELD_KEYS[field];
            return <li key={field}>{key ? t(`missing.${key}`) : field}</li>;
          })}
        </ul>
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="btn-primary text-sm py-2 px-4"
          >
            {tc("close")}
          </button>
        </div>
      </div>
    </div>
  );
}
