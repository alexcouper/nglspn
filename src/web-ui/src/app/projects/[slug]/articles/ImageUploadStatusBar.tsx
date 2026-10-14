"use client";

import { ArrowPathIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";
import type { ImageUploadStatus } from "./useImageUploadStatus";

interface Props {
  status: ImageUploadStatus;
  onDismissError: () => void;
}

export function ImageUploadStatusBar({ status, onDismissError }: Props) {
  const t = useTranslations("articles.imageUpload");
  const tc = useTranslations("common.actions");
  if (status.kind === "idle") return null;

  if (status.kind === "uploading") {
    return (
      <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-2 text-sm text-muted-foreground rounded-t-lg">
        <ArrowPathIcon className="w-4 h-4 animate-spin" />
        {t("uploading")}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 rounded-t-lg"
    >
      <span className="flex-1">{t("failed", { message: status.message })}</span>
      <button
        type="button"
        onClick={onDismissError}
        title={tc("dismiss")}
        className="p-0.5 rounded hover:bg-red-100"
      >
        <XMarkIcon className="w-4 h-4" />
      </button>
    </div>
  );
}
