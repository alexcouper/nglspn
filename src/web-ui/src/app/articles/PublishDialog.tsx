"use client";

import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";

import { Dialog } from "@/components/Dialog";

interface Props {
  isPublishing: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const TITLE_ID = "publish-article-title";

export function PublishDialog({ isPublishing, onClose, onConfirm }: Props) {
  const t = useTranslations("articles.publishDialog");
  const tc = useTranslations("common.actions");
  return (
    <Dialog isOpen onClose={onClose} labelledBy={TITLE_ID}>
      <h2 id={TITLE_ID} className="text-lg font-semibold text-foreground">
        {t("title")}
      </h2>
      <p className="text-sm text-muted-foreground mt-2">
        {t("description")}
      </p>

      <div className="mt-6 flex justify-end gap-2">
        <button
          onClick={onClose}
          disabled={isPublishing}
          className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
        >
          {tc("cancel")}
        </button>
        <button
          onClick={onConfirm}
          disabled={isPublishing}
          className="btn-primary text-sm py-2 px-4"
        >
          {isPublishing ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            tc("publish")
          )}
        </button>
      </div>
    </Dialog>
  );
}
