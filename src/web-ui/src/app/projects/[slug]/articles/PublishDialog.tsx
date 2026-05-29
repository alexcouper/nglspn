"use client";

import { useMemo, useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";

interface Props {
  isPublishing: boolean;
  onClose: () => void;
  onConfirm: (publishedAt: string | null) => void;
}

// Returns the local datetime formatted for an `<input type="datetime-local">`,
// e.g. "2026-05-29T14:32" — using local clock, not UTC.
function nowLocalDatetimeInputValue(): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}`
  );
}

export function PublishDialog({
  isPublishing,
  onClose,
  onConfirm,
}: Props) {
  const [overrideDate, setOverrideDate] = useState(false);
  const [datetime, setDatetime] = useState(nowLocalDatetimeInputValue);

  const isoPublishedAt = useMemo(() => {
    if (!overrideDate) return null;
    const parsed = new Date(datetime);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toISOString();
  }, [overrideDate, datetime]);

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
        <h2 className="text-lg font-semibold text-foreground">Publish article</h2>
        <p className="text-sm text-muted-foreground mt-2">
          Publishing makes the article visible on the project page and notifies
          followers (unless backdated).
        </p>

        <label className="mt-5 flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={overrideDate}
            onChange={(e) => setOverrideDate(e.target.checked)}
            className="accent-accent"
          />
          Set a custom publish date (backdating skips notifications)
        </label>

        {overrideDate && (
          <input
            type="datetime-local"
            value={datetime}
            onChange={(e) => setDatetime(e.target.value)}
            className="mt-3 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12"
          />
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isPublishing}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(isoPublishedAt)}
            disabled={isPublishing}
            className="btn-primary text-sm py-2 px-4"
          >
            {isPublishing ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              "Publish"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
