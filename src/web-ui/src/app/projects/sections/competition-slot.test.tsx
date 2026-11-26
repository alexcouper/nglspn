import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { CompetitionSummary } from "@/lib/api";
import type { CompetitionSlot as Slot } from "@/lib/discover-top";
import { CompetitionSlot } from "./CompetitionSlot";

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- factories

function competition(overrides: Partial<CompetitionSummary> = {}): CompetitionSummary {
  return {
    name: "Tómatur",
    slug: "tomatur",
    submission_deadline: "2026-12-07",
    voting_end_date: null,
    prize_amount: "50000.00",
    status: "accepting_applications",
    image_url: "https://cdn.example/tomatur.png",
    project_count: 2,
    winner: null,
    ...overrides,
  };
}

function acceptingSlot(daysLeft: number, overrides: Partial<CompetitionSummary> = {}): Slot {
  return { state: "accepting", competition: competition(overrides), daysLeft };
}

function votingSlot(daysLeft: number, overrides: Partial<CompetitionSummary> = {}): Slot {
  return {
    state: "voting",
    competition: competition({ name: "Grasker", slug: "grasker", status: "voting", ...overrides }),
    daysLeft,
  };
}

function closedSlot(winnerTitle: string): Slot {
  const winner = { slug: "alkohol-listinn", title: winnerTitle, image_url: "https://cdn.example/winner.png" };
  return {
    state: "closed",
    competition: competition({ name: "Ágúst", slug: "agust", status: "closed", winner }),
    winner,
  };
}

// --------------------------------------------------------------- assertions

function expectText(container: HTMLElement, ...texts: string[]) {
  for (const text of texts) expect(container.textContent).toContain(text);
}

function expectLinksTo(container: HTMLElement, href: string) {
  expect(container.querySelector('[data-testid="competition-slot"]')?.getAttribute("href")).toBe(href);
}

function imageSources(container: HTMLElement): (string | null)[] {
  return Array.from(container.querySelectorAll("img")).map((img) => img.getAttribute("src"));
}

// ---------------------------------------------------------------- the tests

describe("CompetitionSlot", () => {
  it("shows an open round with days left, entries so far, the prize and the verb", async () => {
    const { container, unmount } = await mount(<CompetitionSlot slot={acceptingSlot(11)} />);

    expectText(container, "Open for entries", "Tómatur", "11 days left", "2 entered so far", "50.000 ISK", "Enter your project");
    expectLinksTo(container, "/competitions/tomatur");

    unmount();
  });

  it("leaves the prize out of an open round that has none", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot slot={acceptingSlot(11, { prize_amount: null })} />,
    );

    expect(container.textContent).not.toContain("ISK");

    unmount();
  });

  it("shows voting with days left, the entry count and the verb to rank", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot slot={votingSlot(6, { project_count: 1 })} />,
    );

    expectText(container, "Voting open", "Grasker", "6 days left", "1 entry", "Rank the entries");
    expectLinksTo(container, "/competitions/grasker");

    unmount();
  });

  it("calls the final day of voting the last day", async () => {
    const { container, unmount } = await mount(<CompetitionSlot slot={votingSlot(0)} />);

    expectText(container, "Last day");

    unmount();
  });

  it("shows a closed round as won by its winner, with the winner's image", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot slot={closedSlot("Alkóhól Listinn")} />,
    );

    expectText(container, "Won by Alkóhól Listinn", "Ágúst");
    expect(imageSources(container)).toEqual(["https://cdn.example/winner.png"]);
    expectLinksTo(container, "/competitions/agust");

    unmount();
  });

  it("draws no image when the competition has none", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot slot={acceptingSlot(3, { image_url: null })} />,
    );

    expect(imageSources(container)).toEqual([]);

    unmount();
  });
});
