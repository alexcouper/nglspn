import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { NotificationGroup, NotificationSummary } from "@/lib/api";
import {
  NotificationsProvider,
  useNotifications,
  type NotificationDiffEvent,
} from "./notifications";

vi.mock("@/lib/api", () => ({
  api: {
    notifications: {
      getSummary: vi.fn(),
      listGroups: vi.fn(),
    },
  },
}));

const authState = { value: { isAuthenticated: true } };
vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));

const { api } = await import("@/lib/api");
const getSummary = vi.mocked(api.notifications.getSummary);
const listGroups = vi.mocked(api.notifications.listGroups);

// --------------------------------------------------------------- factories

function articleGroup(id: string): NotificationGroup {
  return {
    kind: "article",
    project: null,
    latest_body_excerpt: "",
    latest_event_at: "2026-11-05T10:00:00Z",
    unread_count: 1,
    article_id: id,
    article_slug: id,
    article_title: `Article ${id}`,
  } as NotificationGroup;
}

function summaryOf(groups: NotificationGroup[]): NotificationSummary {
  return { has_unread: groups.length > 0, unread_group_count: groups.length };
}

/** What the backend holds from now on; a poll sees this state. */
function serverHolds(...groups: NotificationGroup[]) {
  getSummary.mockResolvedValue(summaryOf(groups));
  listGroups.mockResolvedValue(groups);
}

// ------------------------------------------------------------------ mounting

let root: Root | null = null;
let container: HTMLElement | null = null;

async function mountProvider() {
  const diffEvents: NotificationDiffEvent[] = [];
  let latest!: ReturnType<typeof useNotifications>;

  function Probe() {
    const ctx = useNotifications();
    const { subscribeDiff } = ctx;
    useEffect(() => {
      latest = ctx;
    });
    useEffect(
      () => subscribeDiff((event) => diffEvents.push(event)),
      [subscribeDiff],
    );
    return null;
  }

  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <NotificationsProvider>
        <Probe />
      </NotificationsProvider>,
    );
  });

  const poll = () => act(async () => latest.refreshSummary());
  return { diffEvents, poll };
}

const newlyActiveKeys = (events: NotificationDiffEvent[]) =>
  events.flatMap((e) => e.newlyActiveKeys);

beforeEach(() => {
  authState.value = { isAuthenticated: true };
});

afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.clearAllMocks();
});

// ------------------------------------------------------------------- tests

describe("NotificationsProvider diff events", () => {
  it("stays silent about the unread backlog present on first load", async () => {
    serverHolds(articleGroup("a1"), articleGroup("a2"), articleGroup("a3"));

    const { diffEvents } = await mountProvider();

    expect(listGroups).toHaveBeenCalledTimes(1);
    expect(diffEvents).toEqual([]);
  });

  it("announces only the groups that appear after the first load", async () => {
    serverHolds(articleGroup("a1"), articleGroup("a2"));
    const { diffEvents, poll } = await mountProvider();

    serverHolds(articleGroup("a3"), articleGroup("a1"), articleGroup("a2"));
    await poll();

    expect(newlyActiveKeys(diffEvents)).toEqual(["a:a3"]);
  });

  it("announces the first group to arrive when there was no backlog", async () => {
    serverHolds();
    const { diffEvents, poll } = await mountProvider();

    serverHolds(articleGroup("a1"));
    await poll();

    expect(newlyActiveKeys(diffEvents)).toEqual(["a:a1"]);
  });

  it("does not announce a group twice while it stays unread", async () => {
    serverHolds();
    const { diffEvents, poll } = await mountProvider();

    serverHolds(articleGroup("a1"));
    await poll();
    serverHolds(articleGroup("a1"), articleGroup("a2"));
    await poll();

    expect(newlyActiveKeys(diffEvents)).toEqual(["a:a1", "a:a2"]);
  });
});
