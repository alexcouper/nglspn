import { describe, expect, it } from "vitest";
import type { CompetitionSummary, FrontPageArticle } from "@/lib/api";
import { type DiscoverTop, selectDiscoverTop } from "./discover-top";

// --------------------------------------------------------------- factories

const TODAY = new Date("2026-11-26T12:00:00Z");

function article(id: string, overrides: Partial<FrontPageArticle> = {}): FrontPageArticle {
  return {
    id,
    slug: `article-${id}`,
    title: `Article ${id}`,
    summary: "",
    published_at: "2026-11-20T10:00:00Z",
    channel_name: "Updates",
    project_slug: "house",
    project_title: "Naglasúpan",
    author_id: null,
    author_name: null,
    author_avatar_url: null,
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  };
}

function articles(...ids: string[]): FrontPageArticle[] {
  return ids.map((id) => article(id));
}

function competition(
  slug: string,
  overrides: Partial<CompetitionSummary> = {},
): CompetitionSummary {
  return {
    name: slug,
    slug,
    submission_deadline: "2026-12-07",
    voting_end_date: null,
    prize_amount: "50000",
    status: "accepting_applications",
    image_url: null,
    project_count: 2,
    winner: null,
    ...overrides,
  };
}

function voting(slug: string, votingEndDate: string): CompetitionSummary {
  return competition(slug, {
    status: "voting",
    submission_deadline: "2026-11-20",
    voting_end_date: votingEndDate,
  });
}

function accepting(slug: string, submissionDeadline = "2026-12-07"): CompetitionSummary {
  return competition(slug, { submission_deadline: submissionDeadline });
}

function closed(slug: string, winnerTitle: string | null): CompetitionSummary {
  return competition(slug, {
    status: "closed",
    submission_deadline: "2026-10-20",
    voting_end_date: "2026-10-31",
    winner: winnerTitle
      ? { slug: "winner", title: winnerTitle, image_url: "https://cdn.example/winner.png" }
      : null,
  });
}

function select({
  recent = [],
  spotlight = [],
  competitions = [],
}: {
  recent?: FrontPageArticle[] | null;
  spotlight?: FrontPageArticle[] | null;
  competitions?: CompetitionSummary[] | null;
}): DiscoverTop {
  return selectDiscoverTop({ recent, spotlight, competitions, today: TODAY });
}

// --------------------------------------------------------------- assertions

function expectRecent(top: DiscoverTop, lead: string | null, second: string | null) {
  expect(top.lead?.id ?? null).toBe(lead);
  expect(top.second?.id ?? null).toBe(second);
}

function expectSpotlight(top: DiscoverTop, ids: string[]) {
  expect(top.spotlight.map((a) => a.id)).toEqual(ids);
}

function expectSlot(top: DiscoverTop, state: string, slug: string) {
  expect(top.slot?.state).toBe(state);
  expect(top.slot?.competition.slug).toBe(slug);
}

function expectNoSlot(top: DiscoverTop) {
  expect(top.slot).toBeNull();
}

// ---------------------------------------------------------------- the tests

describe("selectDiscoverTop: Recent", () => {
  it("puts the newest article in the lead and the next one second, beside a slot", () => {
    const top = select({ recent: articles("a", "b"), competitions: [accepting("tomatur")] });

    expectRecent(top, "a", "b");
    expectSlot(top, "accepting", "tomatur");
  });

  it("leaves second empty when there is only one recent article", () => {
    expectRecent(select({ recent: articles("a") }), "a", null);
  });

  it("has neither lead nor second when there are no recent articles", () => {
    expectRecent(select({ recent: [] }), null, null);
  });

  it("ignores recent articles past the second", () => {
    expectRecent(select({ recent: articles("a", "b", "c") }), "a", "b");
  });
});

describe("selectDiscoverTop: spotlight", () => {
  it("drops spotlighted articles already shown in Recent, compared by id", () => {
    const top = select({
      recent: articles("a", "b"),
      spotlight: [article("a", { title: "Same id, different title" }), ...articles("c", "d")],
    });

    expectSpotlight(top, ["c", "d"]);
  });

  it("shows at most three spotlighted articles", () => {
    const top = select({ spotlight: articles("c", "d", "e", "f", "g") });

    expectSpotlight(top, ["c", "d", "e"]);
  });

  it("still fills three after removing the two shown in Recent", () => {
    const top = select({
      recent: articles("a", "b"),
      spotlight: articles("a", "b", "c", "d", "e"),
    });

    expectSpotlight(top, ["c", "d", "e"]);
  });

  it("is empty when every spotlighted article is already in Recent", () => {
    const top = select({ recent: articles("a", "b"), spotlight: articles("b", "a") });

    expectSpotlight(top, []);
  });
});

describe("selectDiscoverTop: competition slot", () => {
  it("prefers a competition in voting over one accepting entries", () => {
    const top = select({
      competitions: [accepting("mais"), voting("grasker", "2026-12-02")],
    });

    expectSlot(top, "voting", "grasker");
  });

  it("shows a competition whose voting ends today", () => {
    const top = select({ competitions: [voting("grasker", "2026-11-26")] });

    expectSlot(top, "voting", "grasker");
  });

  it("skips a competition left in voting past its end date", () => {
    const top = select({
      competitions: [voting("grasker", "2026-11-25"), accepting("mais")],
    });

    expectSlot(top, "accepting", "mais");
  });

  it("falls back to the submission deadline when voting has no end date", () => {
    const stale = competition("grasker", {
      status: "voting",
      submission_deadline: "2026-11-20",
      voting_end_date: null,
    });

    expectNoSlot(select({ competitions: [stale] }));
  });

  it("shows a competition accepting entries when none is in voting", () => {
    const top = select({ competitions: [accepting("mais"), closed("tomatur", "Alkóhól Listinn")] });

    expectSlot(top, "accepting", "mais");
  });

  it("counts the days left to the deadline", () => {
    const top = select({ competitions: [accepting("mais", "2026-12-07")] });

    expect(top.slot).toMatchObject({ state: "accepting", daysLeft: 11 });
  });

  it("counts the days left in voting to the voting end date", () => {
    const top = select({ competitions: [voting("grasker", "2026-12-02")] });

    expect(top.slot).toMatchObject({ state: "voting", daysLeft: 6 });
  });

  it("shows the most recently closed competition with its winner when nothing is active", () => {
    const top = select({ competitions: [closed("tomatur", "Alkóhól Listinn")] });

    expectSlot(top, "closed", "tomatur");
    expect(top.slot).toMatchObject({ winner: { title: "Alkóhól Listinn" } });
  });

  it("has no slot when the most recently closed competition has no winner", () => {
    expectNoSlot(select({ competitions: [closed("tomatur", null)] }));
  });

  it("has no slot when there are no competitions", () => {
    expectNoSlot(select({ competitions: [] }));
  });
});

describe("selectDiscoverTop: failed fetches", () => {
  it("treats every null input as empty", () => {
    const top = select({ recent: null, spotlight: null, competitions: null });

    expectRecent(top, null, null);
    expectSpotlight(top, []);
    expectNoSlot(top);
  });

  it("still fills the spotlight when the recent fetch failed", () => {
    const top = select({ recent: null, spotlight: articles("a", "b") });

    expectSpotlight(top, ["a", "b"]);
  });
});
