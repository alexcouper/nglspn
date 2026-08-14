"use client";

import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";

import { Dialog } from "@/components/Dialog";
import { api } from "@/lib/api";
import type { FeedEventSuggestion } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface Props {
  isPublishing: boolean;
  projectRef: string;
  articleId: string;
  onClose: () => void;
  onConfirm: (aboutFeedEventId: string | null) => void;
}

const TITLE_ID = "publish-article-title";
const NOTHING = "";

export function PublishDialog({
  isPublishing,
  projectRef,
  articleId,
  onClose,
  onConfirm,
}: Props) {
  const [suggestions, setSuggestions] = useState<FeedEventSuggestion[]>([]);
  // Defaults to the best guess. Nothing is chosen until suggestions arrive, so
  // publishing before they load links nothing rather than guessing wrong.
  const [selected, setSelected] = useState<string>(NOTHING);

  useEffect(() => {
    let cancelled = false;
    api.articles
      .feedEventSuggestions(projectRef, articleId)
      .then((events) => {
        if (cancelled) return;
        setSuggestions(events);
        if (events.length > 0) setSelected(events[0].id);
      })
      .catch(() => {
        // A failed lookup must not block publishing — the link can be set
        // afterwards, and an unlinked article is valid.
        if (!cancelled) setSuggestions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectRef, articleId]);

  return (
    <Dialog isOpen onClose={onClose} labelledBy={TITLE_ID}>
      <h2 id={TITLE_ID} className="text-lg font-semibold text-foreground">
        Publish article
      </h2>
      <p className="text-sm text-muted-foreground mt-2">
        Publishing makes the article visible to everyone on the project page.
      </p>

      {suggestions.length > 0 && (
        <div className="mt-5">
          <label
            htmlFor="about-feed-event"
            className="block text-sm font-medium text-foreground"
          >
            Is this a write-up of…?
          </label>
          <p className="text-xs text-muted-foreground mt-1">
            Linking it means Latest shows one entry instead of the announcement
            and this article side by side.
          </p>
          <select
            id="about-feed-event"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="mt-2 w-full text-sm border border-border rounded-lg px-3 py-2 bg-white text-foreground"
          >
            {suggestions.map((event) => (
              <option key={event.id} value={event.id}>
                {event.label} · {formatDate(event.occurred_at)}
              </option>
            ))}
            <option value={NOTHING}>Nothing — publish on its own</option>
          </select>
        </div>
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
          onClick={() => onConfirm(selected === NOTHING ? null : selected)}
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
    </Dialog>
  );
}
