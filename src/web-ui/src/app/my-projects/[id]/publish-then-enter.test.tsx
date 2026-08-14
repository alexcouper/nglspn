import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Project } from "@/lib/api";

const { routerCalls } = vi.hoisted(() => ({
  routerCalls: { push: vi.fn(), refresh: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerCalls,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => ({ isReady: true, isLoading: false }),
}));
vi.mock("@/hooks/useImageUpload", () => ({
  useImageUpload: () => ({ uploads: [], uploadFiles: vi.fn(), isUploading: false }),
}));
// Stubbed wholesale: this asserts what happens after publish, and the edit
// surface fetches on mount for reasons of its own.
vi.mock("./EditProjectContent", () => ({ EditProjectContent: () => null }));
vi.mock("@/app/projects/[slug]/ProjectDetailContent", () => ({
  ProjectDetailContent: () => null,
}));
vi.mock("@/lib/api", () => ({
  api: {
    myProjects: {
      get: vi.fn(),
      update: vi.fn(),
      publish: vi.fn(),
      enterCompetition: vi.fn(),
    },
  },
}));

const { api } = await import("@/lib/api");
const { ApiRequestError } = await import("@/lib/api/base");
const { ProjectDetail } = await import("./ProjectDetail");

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

const OPEN_ROUND = {
  competition: {
    id: "june",
    name: "June round",
    slug: "june-round",
    status: "accepting_applications",
    submission_deadline: "2026-06-30",
    image_url: null,
  },
  eligible: true,
  reason: null,
  blocking_entry: null,
};

function project(overrides: Record<string, unknown> = {}): Project {
  return {
    id: "project-1",
    slug: "alpha",
    title: "Alpha",
    tagline: "Does a thing",
    description: "A description",
    website_url: "https://alpha.test",
    status: "draft",
    created_at: "2026-06-01T00:00:00Z",
    images: [],
    tags: [],
    contributors: [],
    won_competitions: [],
    is_community_tipoff: false,
    competition_standing: { entries: [], opportunities: [] },
    ...overrides,
  } as unknown as Project;
}

function buttonLabelled(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === label,
  ) as HTMLButtonElement | undefined;
}

function alertText(container: HTMLElement): string {
  return container.querySelector('[role="alert"]')?.textContent ?? "";
}

async function publishAndOfferARound() {
  vi.mocked(api.myProjects.get).mockResolvedValue(project());
  vi.mocked(api.myProjects.update).mockResolvedValue(project());
  vi.mocked(api.myProjects.publish).mockResolvedValue(
    project({
      status: "pending",
      competition_standing: { entries: [], opportunities: [OPEN_ROUND] },
    }),
  );

  const mounted = await mount(<ProjectDetail projectId="project-1" />);
  await act(async () => {
    buttonLabelled(mounted.container, "Publish")?.click();
  });
  return mounted;
}

describe("the competition offer after publishing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("offers the open round rather than entering it silently", async () => {
    const { container, unmount: cleanup } = await publishAndOfferARound();

    expect(container.textContent).toContain("June round");
    expect(api.myProjects.enterCompetition).not.toHaveBeenCalled();
    expect(routerCalls.push).not.toHaveBeenCalled();
    cleanup();
  });

  it("leaves for the project list once the entry lands", async () => {
    vi.mocked(api.myProjects.enterCompetition).mockResolvedValue(project());
    const { container, unmount: cleanup } = await publishAndOfferARound();

    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    expect(api.myProjects.enterCompetition).toHaveBeenCalledWith(
      "project-1",
      "june",
    );
    expect(routerCalls.push).toHaveBeenCalledWith("/my-projects");
    cleanup();
  });

  it("stays put and says why when the entry is refused", async () => {
    vi.mocked(api.myProjects.enterCompetition).mockRejectedValue(
      new ApiRequestError(
        "Conflict",
        { detail: "This project is already entered in that competition" },
        409,
      ),
    );
    const { container, unmount: cleanup } = await publishAndOfferARound();

    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    // Navigating anyway is what made a refused entry read as an accepted one:
    // the contributor landed on their project list with the reason rendered on
    // the page they had just left.
    expect(routerCalls.push).not.toHaveBeenCalled();
    expect(alertText(container)).toContain("already entered");
    cleanup();
  });

  it("still leaves when only the follow-up read fails", async () => {
    vi.mocked(api.myProjects.enterCompetition).mockResolvedValue(project());
    const { container, unmount: cleanup } = await publishAndOfferARound();
    vi.mocked(api.myProjects.get).mockRejectedValue(new Error("network died"));

    await act(async () => {
      buttonLabelled(container, "Enter")?.click();
    });

    // The write succeeded. A failed re-read is not a reason to tell the
    // contributor their entry didn't happen.
    expect(routerCalls.push).toHaveBeenCalledWith("/my-projects");
    cleanup();
  });
});
