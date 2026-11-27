import { afterEach, describe, expect, it, vi } from "vitest";
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

// Headless Chromium ships without Icelandic locale data, so Intl formats
// "is-IS" numbers the English way there; this makes the test runtime do the same.
function withoutIcelandicNumberFormats() {
  const EnglishNumberFormat = Intl.NumberFormat;
  vi.spyOn(Intl, "NumberFormat").mockImplementation(function (
    _locales?: Intl.LocalesArgument,
    options?: Intl.NumberFormatOptions,
  ) {
    return new EnglishNumberFormat("en-US", options);
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

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

function thumbnailShapes(container: HTMLElement): (string | null)[] {
  return Array.from(container.querySelectorAll("[data-thumbnail]")).map((el) =>
    el.getAttribute("data-thumbnail"),
  );
}

// ---------------------------------------------------------------- the tests

describe("CompetitionSlot", () => {
  it("shows an open round with days left, entries so far, the prize and the verb", async () => {
    const { container, unmount } = await mount(<CompetitionSlot slot={acceptingSlot(11)} />);

    expectText(container, "Open for entries", "Tómatur", "11 days left", "2 entered so far", "50.000 ISK", "Enter your project");
    expectLinksTo(container, "/competitions/tomatur");

    unmount();
  });

  it("writes the prize with a dot between thousands even without Icelandic locale data", async () => {
    withoutIcelandicNumberFormats();
    const { container, unmount } = await mount(
      <CompetitionSlot slot={acceptingSlot(11, { prize_amount: "1250000.00" })} />,
    );

    expectText(container, "1.250.000 ISK");

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

  it("prefers the competition's wide image, drawn wide", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot
        slot={votingSlot(5, { image_wide_url: "https://cdn.example/grasker-wide.jpg" })}
      />,
    );

    expect(imageSources(container)).toEqual(["https://cdn.example/grasker-wide.jpg"]);
    expect(thumbnailShapes(container)).toEqual(["wide"]);

    unmount();
  });

  it("draws the square image square when the competition has no wide one", async () => {
    const { container, unmount } = await mount(
      <CompetitionSlot slot={votingSlot(5, { image_wide_url: null })} />,
    );

    expect(imageSources(container)).toEqual(["https://cdn.example/tomatur.png"]);
    expect(thumbnailShapes(container)).toEqual(["square"]);

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
