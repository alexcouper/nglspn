import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { ProjectCompetitions } from "./ProjectCompetitions";
import type {
  CompetitionOpportunity,
  CompetitionStanding,
  CompetitionSummary,
  ProjectCompetitionEntry,
} from "@/lib/api/my-projects";

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- factories

function competition(
  overrides: Partial<CompetitionSummary> = {},
): CompetitionSummary {
  return {
    id: "competition-1",
    name: "June round",
    slug: "june-round",
    status: "accepting_applications",
    submission_deadline: "2026-06-30",
    ...overrides,
  } as CompetitionSummary;
}

function entry(
  overrides: Partial<ProjectCompetitionEntry> = {},
): ProjectCompetitionEntry {
  return {
    competition: competition(),
    entered_at: "2026-06-04T09:30:00Z",
    entered_via: "manual",
    ...overrides,
  } as ProjectCompetitionEntry;
}

function opportunity(
  overrides: Partial<CompetitionOpportunity> = {},
): CompetitionOpportunity {
  return {
    competition: competition(),
    eligible: true,
    reason: null,
    blocking_entry: null,
    ...overrides,
  } as CompetitionOpportunity;
}

function standing(
  overrides: Partial<CompetitionStanding> = {},
): CompetitionStanding {
  return { entries: [], opportunities: [], ...overrides };
}

function enterButtons(container: HTMLElement): HTMLButtonElement[] {
  return [...container.querySelectorAll("button")].filter((button) =>
    button.textContent?.startsWith("Enter in"),
  ) as HTMLButtonElement[];
}

// -------------------------------------------------------------------- tests

describe("ProjectCompetitions", () => {
  it("names every competition the project is in and links to it", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          entries: [
            entry(),
            entry({
              competition: competition({
                id: "competition-2",
                name: "Winter jam",
                slug: "winter-jam",
                status: "closed",
              }),
            }),
          ],
        })}
        onEnter={vi.fn()}
      />,
    );

    expect(container.textContent).toContain("June round");
    expect(container.textContent).toContain("Winter jam");
    expect(
      container.querySelector('a[href="/competitions/winter-jam"]'),
    ).not.toBeNull();
    cleanup();
  });

  it("marks a competition the project won", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({ entries: [entry()] })}
        wonCompetitionSlugs={["june-round"]}
        onEnter={vi.fn()}
      />,
    );

    expect(container.textContent).toContain("Won");
    cleanup();
  });

  it("offers a control per open round it can enter", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          opportunities: [
            opportunity(),
            opportunity({
              competition: competition({
                id: "competition-2",
                name: "Summer hackathon",
                slug: "summer-hackathon",
              }),
            }),
          ],
        })}
        onEnter={vi.fn()}
      />,
    );

    const buttons = enterButtons(container);
    expect(buttons).toHaveLength(2);
    expect(buttons[0].textContent).toContain("June round");
    expect(buttons[1].textContent).toContain("Summer hackathon");
    cleanup();
  });

  it("explains a blocked round instead of offering a control", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          entries: [entry()],
          opportunities: [
            opportunity({
              competition: competition({ id: "competition-2", name: "July round" }),
              eligible: false,
              reason: "already_in_series",
              blocking_entry: competition(),
            }),
          ],
        })}
        onEnter={vi.fn()}
      />,
    );

    expect(enterButtons(container)).toHaveLength(0);
    expect(container.textContent).toContain("Already in this run");
    expect(container.textContent).toContain("June round");
    cleanup();
  });

  it("states a project-wide reason once rather than per round", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          opportunities: [
            opportunity({ eligible: false, reason: "project_status" }),
            opportunity({
              competition: competition({ id: "competition-2", name: "Summer" }),
              eligible: false,
              reason: "project_status",
            }),
          ],
        })}
        onEnter={vi.fn()}
      />,
    );

    const mentions =
      container.textContent?.match(/can't enter competitions/g) ?? [];
    expect(mentions).toHaveLength(1);
    cleanup();
  });

  it("renders nothing at all for a community tipoff", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          opportunities: [
            opportunity({ eligible: false, reason: "community_project" }),
          ],
        })}
        isCommunityTipoff
        onEnter={vi.fn()}
      />,
    );

    expect(container.textContent).toBe("");
    cleanup();
  });

  it("stays hidden for a tipoff even when no round is open", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing()}
        isCommunityTipoff
        onEnter={vi.fn()}
      />,
    );

    expect(container.textContent).toBe("");
    cleanup();
  });

  it("says no round is open when there is nothing to enter", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions standing={standing()} onEnter={vi.fn()} />,
    );

    expect(container.textContent).toContain("No round is currently open");
    expect(container.textContent).toContain("can enter the next one");
    cleanup();
  });

  it("enters the competition whose control was pressed", async () => {
    const onEnter = vi.fn().mockResolvedValue(undefined);
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({
          opportunities: [
            opportunity(),
            opportunity({
              competition: competition({ id: "competition-2", name: "Summer" }),
            }),
          ],
        })}
        onEnter={onEnter}
      />,
    );

    await act(async () => {
      enterButtons(container)[1].click();
    });

    expect(onEnter).toHaveBeenCalledWith("competition-2");
    cleanup();
  });

  it("shows the error when entry fails", async () => {
    const { container, unmount: cleanup } = await mount(
      <ProjectCompetitions
        standing={standing({ opportunities: [opportunity()] })}
        onEnter={vi.fn()}
        error="That round has closed."
      />,
    );

    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "That round has closed.",
    );
    cleanup();
  });
});
