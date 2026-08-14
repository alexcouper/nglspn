import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Project } from "@/lib/api";
import type { CompetitionSummary } from "@/lib/api/my-projects";

const { searchParams } = vi.hoisted(() => ({
  searchParams: { value: new URLSearchParams() },
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams.value,
}));

vi.mock("@/lib/api", () => ({
  api: {
    myProjects: { list: vi.fn(), enterCompetition: vi.fn() },
  },
}));

const { api } = await import("@/lib/api");
const { EligibleProjectChooser } = await import("./EligibleProjectChooser");

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
    id: "june",
    name: "June round",
    slug: "june-round",
    status: "accepting_applications",
    submission_deadline: "2026-06-30",
    ...overrides,
  } as CompetitionSummary;
}

function project(
  title: string,
  opportunities: { competition: CompetitionSummary; eligible: boolean }[],
): Project {
  return {
    id: `project-${title.toLowerCase()}`,
    title,
    competition_standing: {
      entries: [],
      opportunities: opportunities.map((opportunity) => ({
        ...opportunity,
        reason: null,
        blocking_entry: null,
      })),
    },
  } as unknown as Project;
}

function enterButtons(container: HTMLElement): HTMLButtonElement[] {
  return [...container.querySelectorAll("button")].filter(
    (button) => button.textContent === "Enter",
  ) as HTMLButtonElement[];
}

describe("EligibleProjectChooser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParams.value = new URLSearchParams();
  });

  it("lists only the projects eligible for the named competition", async () => {
    searchParams.value = new URLSearchParams("competition=june");
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Eligible", [{ competition: competition(), eligible: true }]),
      project("Blocked", [{ competition: competition(), eligible: false }]),
      project("Elsewhere", [
        {
          competition: competition({ id: "summer", name: "Summer" }),
          eligible: true,
        },
      ]),
    ]);

    const { container, unmount: cleanup } = await mount(
      <EligibleProjectChooser />,
    );

    expect(container.textContent).toContain("Eligible");
    expect(container.textContent).not.toContain("Blocked");
    expect(container.textContent).not.toContain("Elsewhere");
    expect(container.textContent).toContain("Enter a project in June round");
    cleanup();
  });

  it("lists everything enterable when no competition is named", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
      project("Beta", [
        {
          competition: competition({ id: "summer", name: "Summer" }),
          eligible: true,
        },
      ]),
    ]);

    const { container, unmount: cleanup } = await mount(
      <EligibleProjectChooser />,
    );

    expect(enterButtons(container)).toHaveLength(2);
    cleanup();
  });

  it("renders nothing when no project can be entered", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Blocked", [{ competition: competition(), eligible: false }]),
    ]);

    const { container, unmount: cleanup } = await mount(
      <EligibleProjectChooser />,
    );

    expect(container.textContent).toBe("");
    cleanup();
  });

  it("enters the chosen project into the competition", async () => {
    searchParams.value = new URLSearchParams("competition=june");
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
    ]);
    vi.mocked(api.myProjects.enterCompetition).mockResolvedValue(
      {} as Project,
    );

    const { container, unmount: cleanup } = await mount(
      <EligibleProjectChooser />,
    );
    await act(async () => {
      enterButtons(container)[0].click();
    });

    expect(api.myProjects.enterCompetition).toHaveBeenCalledWith(
      "project-alpha",
      "june",
    );
    expect(container.textContent).toContain("Entered");
    cleanup();
  });

  it("surfaces a failed entry", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
    ]);
    vi.mocked(api.myProjects.enterCompetition).mockRejectedValue(
      new Error("nope"),
    );

    const { container, unmount: cleanup } = await mount(
      <EligibleProjectChooser />,
    );
    await act(async () => {
      enterButtons(container)[0].click();
    });

    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    cleanup();
  });
});
