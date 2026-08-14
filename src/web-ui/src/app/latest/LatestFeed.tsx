"use client";

import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api";
import type { FeedEntry } from "@/lib/api";

import { FeedRow } from "./FeedRow";
import { groupByWeek, weekLabel } from "./feedEntry";

interface Props {
  initialEntries: FeedEntry[];
  initialCursor: string | null;
  lead: FeedEntry | null;
}

export function LatestFeed({ initialEntries, initialCursor, lead }: Props) {
  const [entries, setEntries] = useState(initialEntries);
  const [cursor, setCursor] = useState(initialCursor);
  const [loading, setLoading] = useState(false);

  async function loadMore() {
    if (!cursor || loading) return;
    setLoading(true);
    try {
      const page = await api.feed.page({ before: cursor });
      // The cursor is an event time and events never move, so appending is
      // safe: nothing already shown can arrive again.
      setEntries((current) => [...current, ...page.entries]);
      setCursor(page.next_cursor);
    } finally {
      setLoading(false);
    }
  }

  if (!lead && entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nothing has happened here yet.{" "}
        <Link href="/projects" className="text-accent hover:underline">
          Browse the projects
        </Link>
        .
      </p>
    );
  }

  return (
    <div className="space-y-8">
      {lead && <FeedRow entry={lead} variant="lead" />}

      {groupByWeek(entries).map((group) => (
        <section key={group.key}>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5">
            {weekLabel(group.startsAt)}
          </h2>
          <div className="mt-3 space-y-3">
            {group.entries.map((entry) => (
              <FeedRow key={entry.id} entry={entry} variant="row" />
            ))}
          </div>
        </section>
      ))}

      {cursor && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            className="text-sm font-medium border border-border rounded-md px-4 py-2 hover:border-accent disabled:opacity-60"
          >
            {loading ? "Loading…" : "Show more"}
          </button>
        </div>
      )}
    </div>
  );
}
