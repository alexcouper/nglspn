import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { createElement } from "react";
import { api, type ReviewProject } from "@/lib/api";
import { makeReadyReviewState, makeReviewProjects } from "@/test/factories";
import { MyRanking } from "./MyRanking";

const AUTOSAVE_MS = 500;

let container: HTMLElement;
let root: Root;

async function renderRanking(ranked: ReviewProject[], pool: ReviewProject[]) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      createElement(MyRanking, {
        competitionId: "competition-1",
        competitionName: "Test Competition",
        returnPath: "/competitions/test",
        reviewState: makeReadyReviewState(ranked, pool),
      }),
    );
  });
}

function panel(name: "ranked" | "pool"): HTMLElement {
  const element = container.querySelector(`[data-testid="${name}-panel"]`);
  if (!element) throw new Error(`no ${name} panel rendered`);
  return element as HTMLElement;
}

function titlesIn(name: "ranked" | "pool"): string[] {
  const cards = panel(name).querySelectorAll(
    name === "ranked" ? '[data-testid="ranked-card"]' : '[data-testid="pool-card"]',
  );
  return [...cards].map((card) => card.querySelector("h3")?.textContent ?? "");
}

function ranksIn(): string[] {
  return [...panel("ranked").querySelectorAll('[data-testid="rank-badge"]')].map(
    (badge) => badge.textContent ?? "",
  );
}

function buttonWithLabel(label: string): HTMLButtonElement {
  const button = [...container.querySelectorAll("button")].find((b) =>
    (b.getAttribute("aria-label") ?? b.textContent ?? "").includes(label),
  );
  if (!button) throw new Error(`no button matching "${label}"`);
  return button as HTMLButtonElement;
}

async function click(element: HTMLElement) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

async function clickButtonWithLabel(label: string) {
  await click(buttonWithLabel(label));
}

async function confirmSubmitInDialog() {
  const confirm = container.querySelector('[data-testid="confirm-submit"]');
  if (!confirm) throw new Error("submit dialog is not open");
  await click(confirm as HTMLElement);
}

async function letAutosaveFire() {
  await act(async () => {
    vi.advanceTimersByTime(AUTOSAVE_MS);
  });
}

function lastSavedIds(): string[] {
  const calls = vi.mocked(api.myReview.updateRankings).mock.calls;
  return calls[calls.length - 1][1];
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.spyOn(api.myReview, "updateRankings").mockResolvedValue({ success: true });
  vi.spyOn(api.myReview, "updateStatus").mockResolvedValue(undefined);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.useRealTimers();
});

describe("a competition with no saved ballot", () => {
  it("renders an empty ranking and every project in the pool", async () => {
    const projects = makeReviewProjects(3);

    await renderRanking([], projects);

    expect(titlesIn("ranked")).toEqual([]);
    expect(panel("ranked").querySelector('[data-testid="ranked-empty"]')).not.toBeNull();
    expect(titlesIn("pool")).toEqual(projects.map((p) => p.title));
  });
});

describe("adding a project from the pool", () => {
  it("appends it to the bottom of the ranking and removes it from the pool", async () => {
    const [first, second, third] = makeReviewProjects(3);
    await renderRanking([first], [second, third]);

    await clickButtonWithLabel(`Add ${second.title}`);

    expect(titlesIn("ranked")).toEqual([first.title, second.title]);
    expect(ranksIn()).toEqual(["1", "2"]);
    expect(titlesIn("pool")).toEqual([third.title]);
  });

  it("keeps the pool tab active and updates the ranked count", async () => {
    const [ranked, poolProject] = makeReviewProjects(2);
    await renderRanking([ranked], [poolProject]);
    await clickButtonWithLabel("Unranked (1)");

    await clickButtonWithLabel(`Add ${poolProject.title}`);

    expect(buttonWithLabel("Unranked").getAttribute("aria-selected")).toBe("true");
    expect(buttonWithLabel("My ranking").textContent).toContain("My ranking (2)");
  });

  it("persists the new ballot", async () => {
    const [ranked, poolProject] = makeReviewProjects(2);
    await renderRanking([ranked], [poolProject]);

    await clickButtonWithLabel(`Add ${poolProject.title}`);
    await letAutosaveFire();

    expect(lastSavedIds()).toEqual([ranked.id, poolProject.id]);
  });
});

describe("removing a ranked project", () => {
  it("closes the position gap and returns the project to the pool", async () => {
    const [first, middle, last, unranked] = makeReviewProjects(4);
    await renderRanking([first, middle, last], [unranked]);

    await clickButtonWithLabel(`Remove ${middle.title}`);

    expect(titlesIn("ranked")).toEqual([first.title, last.title]);
    expect(ranksIn()).toEqual(["1", "2"]);
    expect(titlesIn("pool")).toContain(middle.title);
  });

  it("persists the shortened ballot", async () => {
    const [first, second] = makeReviewProjects(2);
    await renderRanking([first, second], []);

    await clickButtonWithLabel(`Remove ${first.title}`);
    await letAutosaveFire();

    expect(lastSavedIds()).toEqual([second.id]);
  });
});

describe("reordering the ranked list", () => {
  it("moves a project one position with the up control", async () => {
    const [first, second] = makeReviewProjects(2);
    await renderRanking([first, second], []);

    await clickButtonWithLabel(`Move ${second.title} up`);

    expect(titlesIn("ranked")).toEqual([second.title, first.title]);
  });
});

describe("submitting an empty ballot", () => {
  it("asks for confirmation that nothing will be ranked", async () => {
    await renderRanking([], makeReviewProjects(2));

    await clickButtonWithLabel("Submit Ranking");

    const body = container.querySelector('[data-testid="submit-dialog-body"]');
    expect(body?.textContent).toContain("not ranked any projects");
  });

  it("leaves the review unchanged when the confirmation is cancelled", async () => {
    await renderRanking([], makeReviewProjects(2));
    await clickButtonWithLabel("Submit Ranking");

    await clickButtonWithLabel("Cancel");

    expect(api.myReview.updateStatus).not.toHaveBeenCalled();
    expect(buttonWithLabel("Submit Ranking")).toBeTruthy();
  });
});

describe("reordering immediately before submitting", () => {
  it("persists the reorder before the status change", async () => {
    const [first, second] = makeReviewProjects(2);
    await renderRanking([first, second], []);

    await clickButtonWithLabel(`Move ${second.title} up`);
    await clickButtonWithLabel("Submit Ranking");
    await confirmSubmitInDialog();

    expect(lastSavedIds()).toEqual([second.id, first.id]);
    const savedAt = vi.mocked(api.myReview.updateRankings).mock.invocationCallOrder.at(-1)!;
    const statusAt = vi.mocked(api.myReview.updateStatus).mock.invocationCallOrder[0];
    expect(savedAt).toBeLessThan(statusAt);
  });
});
