import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { EnterCompetitionDialog } from "./EnterCompetitionDialog";
import type {
  CompetitionOpportunity,
  CompetitionSummary,
} from "@/lib/api/my-projects";

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

function buttonLabelled(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === label,
  ) as HTMLButtonElement | undefined;
}

describe("EnterCompetitionDialog", () => {
  it("lists every open round with its deadline", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[
          opportunity(),
          opportunity({
            competition: competition({
              id: "competition-2",
              name: "Summer hackathon",
              submission_deadline: "2026-07-15",
            }),
          }),
        ]}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    expect(container.textContent).toContain("June round");
    expect(container.textContent).toContain("Summer hackathon");
    expect(container.textContent).toContain("June 30, 2026");
    cleanup();
  });

  it("renders nothing when no round is on offer", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[]}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    expect(container.querySelector('[role="dialog"]')).toBeNull();
    cleanup();
  });

  it("enters the round whose button was pressed", async () => {
    const onEnter = vi.fn().mockResolvedValue(undefined);
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[
          opportunity(),
          opportunity({
            competition: competition({ id: "competition-2", name: "Summer" }),
          }),
        ]}
        onEnter={onEnter}
        onDismiss={vi.fn()}
      />,
    );

    await act(async () => {
      [...container.querySelectorAll("button")]
        .filter((button) => button.textContent === "Enter")[1]
        .click();
    });

    expect(onEnter).toHaveBeenCalledWith("competition-2");
    cleanup();
  });

  it("dismisses without entering", async () => {
    const onEnter = vi.fn();
    const onDismiss = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={onEnter}
        onDismiss={onDismiss}
      />,
    );

    await act(async () => {
      buttonLabelled(container, "Not now")?.click();
    });

    expect(onDismiss).toHaveBeenCalled();
    expect(onEnter).not.toHaveBeenCalled();
    cleanup();
  });
});
