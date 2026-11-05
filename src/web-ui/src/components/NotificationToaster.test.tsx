import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { NotificationGroup } from "@/lib/api";
import type { NotificationDiffEvent } from "@/contexts/notifications";
import { ToastsProvider } from "@/contexts/toasts";
import { ToastContainer } from "./ToastContainer";
import { NotificationToaster } from "./NotificationToaster";

const router = { push: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

// The toaster only listens; the test plays the provider and emits diffs.
let emitDiff: (event: NotificationDiffEvent) => void = () => {};
vi.mock("@/contexts/notifications", () => ({
  useNotifications: () => ({
    subscribeDiff: (listener: (event: NotificationDiffEvent) => void) => {
      emitDiff = listener;
      return () => {
        emitDiff = () => {};
      };
    },
    markArticleRead: vi.fn().mockResolvedValue(undefined),
  }),
}));

// --------------------------------------------------------------- factories

function articleGroup(id: string): NotificationGroup {
  return {
    kind: "article",
    project: { id: "p1", slug: "nglspn", title: "Naglasúpan", image_url: null },
    latest_body_excerpt: "",
    latest_event_at: "2026-11-05T10:00:00Z",
    unread_count: 1,
    article_id: id,
    article_slug: id,
    article_title: `Article ${id}`,
    channel_name: "Updates",
  } as NotificationGroup;
}

function arrivalOf(...groups: NotificationGroup[]): NotificationDiffEvent {
  const groupsByKey = new Map<string, NotificationGroup>();
  for (const g of groups) groupsByKey.set(`a:${g.article_id}`, g);
  return { newlyActiveKeys: [...groupsByKey.keys()], groupsByKey };
}

const arrivals = (count: number) =>
  arrivalOf(...Array.from({ length: count }, (_, i) => articleGroup(`a${i + 1}`)));

// ------------------------------------------------------------------ mounting

let root: Root | null = null;
let container: HTMLElement | null = null;

async function mountToaster() {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <ToastsProvider>
        <NotificationToaster />
        <ToastContainer />
      </ToastsProvider>,
    );
  });
}

const notify = (event: NotificationDiffEvent) => act(async () => emitDiff(event));

function visibleToasts(): string[] {
  return Array.from(container!.querySelectorAll('[role="status"]')).map(
    (el) => el.textContent ?? "",
  );
}

function tabIs(state: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

beforeEach(() => {
  tabIs("visible");
});

afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.clearAllMocks();
});

// ------------------------------------------------------------------- tests

describe("NotificationToaster", () => {
  it("shows one toast per group when a few arrive", async () => {
    await mountToaster();

    await notify(arrivals(2));

    expect(visibleToasts()).toHaveLength(2);
    expect(visibleToasts()[0]).toContain("Naglasúpan published Article a1 in Updates");
    expect(visibleToasts()[1]).toContain("Naglasúpan published Article a2 in Updates");
  });

  it("collapses a burst into a single count that leads to the notifications page", async () => {
    await mountToaster();

    await notify(arrivals(5));

    expect(visibleToasts()).toEqual(["5 new notifications"]);
    await act(async () => {
      container!.querySelector<HTMLElement>('[role="status"]')!.click();
    });
    expect(router.push).toHaveBeenCalledWith("/notifications");
  });

  it("shows nothing while the tab is hidden", async () => {
    await mountToaster();
    tabIs("hidden");

    await notify(arrivals(2));

    expect(visibleToasts()).toEqual([]);
  });

  it("does not repeat a group that was toasted moments ago", async () => {
    await mountToaster();

    await notify(arrivals(1));
    await notify(arrivals(1));

    expect(visibleToasts()).toHaveLength(1);
  });
});
