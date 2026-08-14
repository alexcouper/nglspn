import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Competition } from "@/lib/api";

const { authState } = vi.hoisted(() => ({
  authState: { value: { isAuthenticated: true, isLoading: false } },
}));

vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api", () => ({
  api: {
    myProjects: { list: vi.fn(), enterCompetition: vi.fn() },
    myReview: { getCompetition: vi.fn() },
  },
}));

const { api } = await import("@/lib/api");
const { CompetitionReveal } = await import("./CompetitionReveal");

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
  id: "june",
  name: "June round",
  slug: "june-round",
  status: "accepting_applications",
  start_date: "2026-06-01",
  submission_deadline: "2026-06-30",
  voting_end_date: "2026-07-15",
  prize_amount: null,
  project_count: 3,
  projects: [],
  image_url: null,
  image_wide_url: null,
  image_wide_winner_url: null,
  quote: null,
  winner: null,
} as unknown as Competition;

function submitButton(container: HTMLElement) {
  return [...container.querySelectorAll("button")].find((button) =>
    button.textContent?.includes("Submit a Project"),
  ) as HTMLButtonElement | undefined;
}

describe("the competition's submit call to action", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.value = { isAuthenticated: true, isLoading: false };
    vi.mocked(api.myProjects.list).mockResolvedValue([]);
  });

  it("opens the chooser rather than navigating, when signed in", async () => {
    const { container, unmount: cleanup } = await mount(
      <CompetitionReveal initialCompetition={OPEN_ROUND} />,
    );

    const button = submitButton(container);
    expect(button).toBeDefined();
    expect(container.querySelector('a[href^="/submit"]')).toBeNull();

    await act(async () => {
      button?.click();
    });

    expect(container.textContent).toContain("Enter a project in June round");
    expect(api.myProjects.list).toHaveBeenCalled();
    cleanup();
  });

  it("links an anonymous visitor to project creation", async () => {
    authState.value = { isAuthenticated: false, isLoading: false };

    const { container, unmount: cleanup } = await mount(
      <CompetitionReveal initialCompetition={OPEN_ROUND} />,
    );

    expect(submitButton(container)).toBeUndefined();
    expect(container.querySelector('a[href="/create"]')).not.toBeNull();
    expect(api.myProjects.list).not.toHaveBeenCalled();
    cleanup();
  });
});
