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
    image_url: "https://example.com/june.jpg",
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

function alertText(container: HTMLElement): string {
  return container.querySelector('[role="alert"]')?.textContent ?? "";
}

function radios(container: HTMLElement): HTMLInputElement[] {
  return [
    ...container.querySelectorAll('input[type="radio"]'),
  ] as HTMLInputElement[];
}

const TWO_ROUNDS = [
  opportunity(),
  opportunity({
    competition: competition({
      id: "competition-2",
      name: "Summer hackathon",
      submission_deadline: "2026-07-15",
    }),
  }),
];

describe("EnterCompetitionDialog", () => {
  it("lists every open round with its deadline", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={TWO_ROUNDS}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    expect(container.textContent).toContain("June round");
    expect(container.textContent).toContain("Summer hackathon");
    expect(container.textContent).toContain("June 30, 2026");
    cleanup();
  });

  it("says the project is under review rather than published", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    expect(container.textContent).not.toContain("Published");
    expect(container.textContent).toContain("goes live once we've reviewed it");
    expect(container.textContent).toContain("on approval");
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

    expect(container.querySelector("dialog")).toBeNull();
    cleanup();
  });

  it("enters a lone round without asking which", async () => {
    const onEnter = vi.fn().mockResolvedValue(undefined);
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={onEnter}
        onDismiss={vi.fn()}
      />,
    );

    expect(radios(container)).toHaveLength(0);
    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(onEnter).toHaveBeenCalledWith("competition-1");
    cleanup();
  });

  it("enters the selected round rather than the first", async () => {
    const onEnter = vi.fn().mockResolvedValue(undefined);
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={TWO_ROUNDS}
        onEnter={onEnter}
        onDismiss={vi.fn()}
      />,
    );

    await act(async () => {
      radios(container)[1].click();
    });
    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(onEnter).toHaveBeenCalledWith("competition-2");
    expect(onEnter).toHaveBeenCalledTimes(1);
    cleanup();
  });

  it("enters the first round when the offer is taken as it stands", async () => {
    const onEnter = vi.fn().mockResolvedValue(undefined);
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={TWO_ROUNDS}
        onEnter={onEnter}
        onDismiss={vi.fn()}
      />,
    );

    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(onEnter).toHaveBeenCalledWith("competition-1");
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

  it("shows the reason an entry was refused", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
        error="This project is already entered in that competition"
      />,
    );

    expect(alertText(container)).toContain(
      "This project is already entered in that competition",
    );
    cleanup();
  });

  it("says something when onEnter rejects instead of reporting", async () => {
    const onEnter = vi.fn().mockRejectedValue(new Error("network died"));
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={onEnter}
        onDismiss={vi.fn()}
      />,
    );

    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(alertText(container)).toContain("Couldn't enter this competition");
    expect(buttonLabelled(container, "Enter")?.disabled).toBe(false);
    cleanup();
  });

  it("puts the two actions side by side in one footer", async () => {
    const { container, unmount: cleanup } = await mount(
      <EnterCompetitionDialog
        opportunities={[opportunity()]}
        onEnter={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    const enter = buttonLabelled(container, "Enter");
    const notNow = buttonLabelled(container, "Not now");

    expect(enter?.parentElement).toBe(notNow?.parentElement);
    cleanup();
  });
});
