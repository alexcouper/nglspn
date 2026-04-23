"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslations, useLocale } from "next-intl";
import { useEditableMessages } from "@/contexts/editable-messages";
import { useAuth } from "@/contexts/auth";
import {
  getTranslationDetail,
  patchTranslation,
  type TranslationDetail,
} from "@/lib/i18n/api";
import type { Locale } from "@/i18n/config";
import { ChipsEditor, validateAgainstReference } from "./TranslationChips";

const POPOVER_WIDTH = 360;

export function TranslationPopover({
  tKey,
  anchor,
  onClose,
}: {
  tKey: string;
  anchor: HTMLElement;
  onClose: () => void;
}) {
  const t = useTranslations("translatePopover");
  const locale = useLocale() as Locale;
  const { applyOverride, readEnglish } = useEditableMessages();
  const { getToken } = useAuth();
  const englishReference = readEnglish(tKey) ?? "";

  const [detail, setDetail] = useState<TranslationDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmStale, setConfirmStale] = useState<{
    seconds: number;
    user: string | null;
  } | null>(null);

  const validation = validateAgainstReference(englishReference, draft);

  const portalRoot = typeof document !== "undefined" ? document.body : null;
  const position = computeAnchoredPosition(anchor);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getTranslationDetail(locale, tKey)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
        setDraft(d.text);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [locale, tKey]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onMouseDown(e: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        !anchor.contains(e.target as Node)
      ) {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onMouseDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onMouseDown);
    };
  }, [anchor, onClose]);

  if (!portalRoot) return null;

  async function handleSave(forceOverwrite = false) {
    setBusy(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      if (!forceOverwrite) {
        const fresh = await getTranslationDetail(locale, tKey);
        if (
          detail?.updated_at &&
          fresh.updated_at &&
          fresh.updated_at !== detail.updated_at
        ) {
          const seconds = Math.max(
            1,
            Math.round((Date.now() - new Date(fresh.updated_at).getTime()) / 1000),
          );
          const lastEditor = fresh.history[0]?.changed_by ?? null;
          setConfirmStale({ seconds, user: lastEditor });
          setBusy(false);
          return;
        }
      }

      const updated = await patchTranslation(locale, tKey, draft, token);
      applyOverride(tKey, updated.text);
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div
      ref={popoverRef}
      role="dialog"
      aria-label={t("title")}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      className="fixed z-[100] bg-white border border-border rounded-lg shadow-xl p-4"
      style={{
        top: position.top,
        left: position.left,
        width: POPOVER_WIDTH,
      }}
    >
      <div className="text-xs text-slate-500 mb-2">{tKey}</div>

      <ChipsEditor value={draft} onChange={setDraft} rows={3} />

      {locale !== "en" && (
        <div className="mt-2 text-xs">
          <div className="text-slate-500 uppercase tracking-wide mb-0.5">
            {t("englishReference")}
          </div>
          <div className="text-slate-700">{englishReference}</div>
        </div>
      )}

      {!validation.ok && (
        <div className="mt-2 text-xs text-amber-700">{t("placeholderLost")}</div>
      )}

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-slate-500 hover:text-slate-900 select-none">
          {t("history")}{" "}
          {detail && detail.history.length > 0 ? `(${detail.history.length})` : ""}
        </summary>
        {detail && detail.history.length === 0 && (
          <div className="mt-1 text-slate-400">{t("noHistory")}</div>
        )}
        {detail && detail.history.length > 0 && (
          <ul className="mt-1 space-y-1">
            {detail.history.map((entry) => (
              <li
                key={entry.changed_at}
                className="border-l-2 border-slate-200 pl-2"
              >
                <div className="text-slate-500">
                  {entry.changed_by ?? "system"} · {formatRelative(entry.changed_at)}
                </div>
                <div className="text-slate-700 truncate">{entry.new_text}</div>
                <button
                  type="button"
                  onClick={() => setDraft(entry.new_text)}
                  className="text-accent hover:underline"
                >
                  {t("revertToThis")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </details>

      {confirmStale && (
        <div className="mt-2 text-xs text-amber-700" role="alert">
          {t("concurrencyWarning", {
            seconds: confirmStale.seconds,
            user: confirmStale.user ?? "someone",
          })}
          <button
            type="button"
            onClick={() => {
              setConfirmStale(null);
              handleSave(true);
            }}
            className="ml-2 underline hover:text-amber-900"
          >
            {t("concurrencyConfirm")}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-2 text-xs text-red-600" role="alert">
          {error}
        </div>
      )}

      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 text-sm text-slate-600 hover:text-slate-900"
          disabled={busy}
        >
          {t("cancel")}
        </button>
        <button
          type="button"
          onClick={() => handleSave(false)}
          disabled={busy || !detail || !validation.ok}
          className="px-3 py-1 text-sm bg-accent text-white rounded hover:bg-accent-hover disabled:opacity-50"
        >
          {busy ? t("saving") : t("save")}
        </button>
      </div>
    </div>,
    portalRoot,
  );
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function computeAnchoredPosition(anchor: HTMLElement) {
  if (typeof window === "undefined") return { top: 0, left: 0 };
  const r = anchor.getBoundingClientRect();
  return {
    top: r.bottom + 4,
    left: Math.max(8, Math.min(r.left, window.innerWidth - POPOVER_WIDTH - 8)),
  };
}
