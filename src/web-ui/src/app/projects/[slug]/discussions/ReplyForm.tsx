"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useAutoResize } from "@/hooks/useAutoResize";

interface ReplyFormProps {
  onSubmit: (body: string) => Promise<void>;
  onCancel: () => void;
}

export function ReplyForm({ onSubmit, onCancel }: ReplyFormProps) {
  const t = useTranslations("discussions.replyForm");
  const tc = useTranslations("common.actions");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { ref: textareaRef, resize } = useAutoResize();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;

    setSubmitting(true);
    try {
      await onSubmit(body.trim());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-1">
      <div className="flex gap-2">
      <textarea
        ref={textareaRef}
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
          resize();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !submitting && body.trim()) {
            e.preventDefault();
            handleSubmit(e);
          }
          if (e.key === "Escape" && !submitting) {
            e.preventDefault();
            onCancel();
          }
        }}
        placeholder={t("placeholder")}
        rows={2}
        className="input flex-1 resize-none overflow-hidden text-sm"
        autoFocus
      />
      <div className="flex flex-col gap-1">
        <button
          type="submit"
          disabled={submitting || !body.trim()}
          className="btn-primary text-xs disabled:opacity-50"
        >
          {submitting ? "..." : t("submit")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {tc("cancel")}
        </button>
      </div>
      </div>
      <p className={`text-[11px] text-muted-foreground ${body.trim() ? "" : "invisible"}`}>
        {t.rich("keyboardHint", {
          kbd: (chunks) => <kbd className="font-medium">{chunks}</kbd>,
        })}
      </p>
    </form>
  );
}
