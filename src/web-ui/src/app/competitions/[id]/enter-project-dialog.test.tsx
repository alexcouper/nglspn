import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Project } from "@/lib/api";
import type { CompetitionSummary } from "@/lib/api/my-projects";

vi.mock("@/lib/api", () => ({
  api: {
    myProjects: { list: vi.fn(), enterCompetition: vi.fn() },
  },
}));

const { api } = await import("@/lib/api");
const { EnterProjectDialog } = await import("./EnterProjectDialog");

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

const JUNE = {
  id: "june",
  name: "June round",
  submission_deadline: "2026-06-30",
};

function competition(
  overrides: Partial<CompetitionSummary> = {},
): CompetitionSummary {
  return {
    id: "june",
    name: "June round",
    slug: "june-round",
    status: "accepting_applications",
    submission_deadline: "2026-06-30",
    image_url: null,
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
    tagline: `${title} does a thing`,
    status: "pending",
    images: [],
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

/** A project already holding an entry in `competition` — so the server reports
 *  it under entries and never as an opportunity. */
function enteredProject(
  title: string,
  status: string,
  entered: CompetitionSummary = competition(),
): Project {
  return {
    id: `project-${title.toLowerCase()}`,
    title,
    tagline: `${title} does a thing`,
    status,
    images: [],
    competition_standing: {
      entries: [
        { competition: entered, entered_at: "2026-06-04T09:30:00Z", entered_via: "manual" },
      ],
      opportunities: [],
    },
  } as unknown as Project;
}

function buttonLabelled(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === label,
  ) as HTMLButtonElement | undefined;
}

function radios(container: HTMLElement): HTMLInputElement[] {
  return [
    ...container.querySelectorAll('input[type="radio"]'),
  ] as HTMLInputElement[];
}

async function open(props: Partial<Record<string, unknown>> = {}) {
  return mount(
    <EnterProjectDialog
      competition={JUNE}
      isOpen
      onClose={vi.fn()}
      onEntered={vi.fn()}
      {...props}
    />,
  );
}

describe("EnterProjectDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.myProjects.list).mockResolvedValue([]);
  });

  it("lists only the projects eligible for this competition", async () => {
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

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain("Eligible");
    expect(container.textContent).not.toContain("Blocked");
    expect(container.textContent).not.toContain("Elsewhere");
    expect(container.textContent).toContain("June round");
    cleanup();
  });

  it("enters the selected project into this competition", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
      project("Beta", [{ competition: competition(), eligible: true }]),
    ]);
    vi.mocked(api.myProjects.enterCompetition).mockResolvedValue({} as Project);
    const onEntered = vi.fn();

    const { container, unmount: cleanup } = await open({ onEntered });
    await act(async () => {
      radios(container)[1].click();
    });
    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(api.myProjects.enterCompetition).toHaveBeenCalledWith(
      "project-beta",
      "june",
    );
    expect(onEntered).toHaveBeenCalled();
    cleanup();
  });

  it("enters a lone project without asking which", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
    ]);
    vi.mocked(api.myProjects.enterCompetition).mockResolvedValue({} as Project);

    const { container, unmount: cleanup } = await open();

    expect(radios(container)).toHaveLength(0);
    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(api.myProjects.enterCompetition).toHaveBeenCalledWith(
      "project-alpha",
      "june",
    );
    cleanup();
  });

  it("reports a pending project as in the round, awaiting review", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      enteredProject("Fluglest", "pending"),
    ]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain("Already in this round");
    expect(container.textContent).toContain("Fluglest");
    expect(container.textContent).toContain("Awaiting review");
    expect(container.textContent).not.toContain(
      "None of your projects can enter this round",
    );
    cleanup();
  });

  it("reports an approved project as live in the round", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      enteredProject("Kortavefur", "approved"),
    ]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain("Live in the round");
    cleanup();
  });

  it("says nothing else can enter when everything is already in", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      enteredProject("Fluglest", "pending"),
    ]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain(
      "Nothing else of yours can enter this round",
    );
    expect(container.querySelector('a[href="/create"]')).not.toBeNull();
    expect(buttonLabelled(container, "Enter")).toBeUndefined();
    cleanup();
  });

  it("shows both what is in and what can still be entered", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      enteredProject("Fluglest", "pending"),
      project("Bokasafn", [{ competition: competition(), eligible: true }]),
    ]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain("Already in this round");
    expect(container.textContent).toContain("Fluglest");
    expect(container.textContent).toContain("Bokasafn");
    expect(buttonLabelled(container, "Enter")).toBeDefined();
    cleanup();
  });

  it("tells a user with no projects that they have none yet", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain("haven't added a project yet");
    expect(container.querySelector('a[href="/create"]')).not.toBeNull();
    expect(buttonLabelled(container, "Enter")).toBeUndefined();
    cleanup();
  });

  it("tells a user whose projects are all blocked why", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Blocked", [{ competition: competition(), eligible: false }]),
    ]);

    const { container, unmount: cleanup } = await open();

    expect(container.textContent).toContain(
      "None of your projects can enter this round",
    );
    expect(container.querySelector('a[href="/create"]')).not.toBeNull();
    cleanup();
  });

  it("dismissing enters nothing", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
    ]);
    const onClose = vi.fn();

    const { container, unmount: cleanup } = await open({ onClose });
    await act(async () => {
      buttonLabelled(container, "Close")?.click();
    });

    expect(onClose).toHaveBeenCalled();
    expect(api.myProjects.enterCompetition).not.toHaveBeenCalled();
    cleanup();
  });

  it("surfaces a failed entry", async () => {
    vi.mocked(api.myProjects.list).mockResolvedValue([
      project("Alpha", [{ competition: competition(), eligible: true }]),
    ]);
    vi.mocked(api.myProjects.enterCompetition).mockRejectedValue(
      new Error("nope"),
    );

    const { container, unmount: cleanup } = await open();
    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    cleanup();
  });

  it("does not fetch until it is opened", async () => {
    const { unmount: cleanup } = await mount(
      <EnterProjectDialog
        competition={JUNE}
        isOpen={false}
        onClose={vi.fn()}
        onEntered={vi.fn()}
      />,
    );

    expect(api.myProjects.list).not.toHaveBeenCalled();
    cleanup();
  });
});
