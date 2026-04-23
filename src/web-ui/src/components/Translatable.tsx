"use client";

import { useState, type ReactNode } from "react";
import { useEditableMessages } from "@/contexts/editable-messages";
import { TranslationPopover } from "./TranslationPopover";

export function Translatable({
  tKey,
  children,
}: {
  /** Dotted i18n key, e.g. "nav.profile". */
  tKey: string;
  children: ReactNode;
}) {
  const { editMode, isFallback } = useEditableMessages();
  const [popoverAnchor, setPopoverAnchor] = useState<HTMLElement | null>(null);

  if (!editMode) {
    return <>{children}</>;
  }

  const fallback = isFallback(tKey);

  return (
    <span
      className={
        "relative group/translatable inline-block " +
        (fallback ? "underline decoration-dotted decoration-amber-400/60" : "")
      }
      data-i18n-key={tKey}
    >
      {children}
      <button
        type="button"
        aria-label={`Edit translation for ${tKey}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setPopoverAnchor(e.currentTarget);
        }}
        className="absolute -top-1 -right-3 opacity-0 group-hover/translatable:opacity-100 transition-opacity p-0.5 rounded bg-white shadow-sm border border-border text-slate-500 hover:text-slate-900"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z"
          />
        </svg>
      </button>
      {popoverAnchor && (
        <TranslationPopover
          tKey={tKey}
          anchor={popoverAnchor}
          onClose={() => setPopoverAnchor(null)}
        />
      )}
    </span>
  );
}
