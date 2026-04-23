"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEditableMessages } from "@/contexts/editable-messages";
import { setEditModeCookie } from "@/lib/i18n/edit-mode-cookie.client";

export function EditModeToggle({ onClick }: { onClick?: () => void }) {
  const { editMode } = useEditableMessages();
  const router = useRouter();
  const t = useTranslations("nav");

  return (
    <button
      type="button"
      role="menuitem"
      onClick={() => {
        setEditModeCookie(!editMode);
        onClick?.();
        router.refresh();
      }}
      className="block w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
    >
      {editMode ? t("editTranslationsOn") : t("editTranslationsOff")}
    </button>
  );
}
