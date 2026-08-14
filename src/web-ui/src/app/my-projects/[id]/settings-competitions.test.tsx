import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Project } from "@/lib/api";
import type { CompetitionStanding } from "@/lib/api/my-projects";
import type { ProjectFormData } from "./ProjectDetail";

// Stubbed because they fetch on mount and have nothing to do with what this
// asserts: where the competitions section lives.
vi.mock("@/components/TagSidebarSelector", () => ({
  TagSidebarSelector: () => null,
}));
vi.mock("./MyProjectArticles", () => ({ MyProjectArticles: () => null }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

const { EditProjectContent } = await import("./EditProjectContent");

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

const STANDING: CompetitionStanding = {
  entries: [],
  opportunities: [
    {
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
    },
  ],
} as unknown as CompetitionStanding;

const PROJECT = {
  id: "project-1",
  slug: "alpha",
  title: "Alpha",
  tagline: "Does a thing",
  status: "pending",
  created_at: "2026-05-01T10:00:00Z",
  is_community_tipoff: false,
  won_competitions: [],
  creator: { first_name: "Ada", last_name: "Byron" },
  tags: [],
  images: [],
} as unknown as Project;

const FORM: ProjectFormData = {
  title: "Alpha",
  tagline: "Does a thing",
  website_url: "https://alpha.example",
  description: "",
  tag_ids: [],
};

async function renderEditMode(standing: CompetitionStanding | null) {
  return mount(
    <EditProjectContent
      project={PROJECT}
      formData={FORM}
      onChange={vi.fn()}
      onTagsChange={vi.fn()}
      images={[]}
      uploads={[]}
      isUploading={false}
      onFilesSelected={vi.fn()}
      onUpdateImageRoles={vi.fn()}
      onDeleteImage={vi.fn()}
      iconImage={null}
      onIconFilesSelected={vi.fn()}
      onDeleteIcon={vi.fn()}
      competitionStanding={standing}
      competitionError=""
      onEnterCompetition={vi.fn()}
    />,
  );
}

function tabLabelled(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === label,
  ) as HTMLButtonElement | undefined;
}

function settingsTab(container: HTMLElement): HTMLElement | null {
  return container.querySelector('[data-testid="settings-tab"]');
}

/** Every tab's content is in the DOM; the inactive ones are hidden. */
function isShowing(panel: HTMLElement | null): boolean {
  return panel?.parentElement?.classList.contains("hidden") === false;
}

describe("competitions in edit mode", () => {
  it("lives in the Settings tab, not beside the content", async () => {
    const { container, unmount: cleanup } = await renderEditMode(STANDING);

    const settings = settingsTab(container);
    expect(settings?.textContent).toContain("Competitions");
    expect(settings?.textContent).toContain("June round");
    // Nowhere else on the page — the whole point of the move.
    expect(container.textContent?.match(/June round/g)).toHaveLength(2);
    expect(isShowing(settings)).toBe(false);

    await act(async () => {
      tabLabelled(container, "Settings")?.click();
    });

    expect(isShowing(settingsTab(container))).toBe(true);
    cleanup();
  });

  it("shows nothing about competitions where there is no standing", async () => {
    const { container, unmount: cleanup } = await renderEditMode(null);

    await act(async () => {
      tabLabelled(container, "Settings")?.click();
    });

    expect(container.textContent).not.toContain("Competitions");
    cleanup();
  });

  it("shows nothing about competitions for a tipoff", async () => {
    const { container, unmount: cleanup } = await mount(
      <EditProjectContent
        project={{ ...PROJECT, is_community_tipoff: true } as Project}
        formData={FORM}
        onChange={vi.fn()}
        onTagsChange={vi.fn()}
        images={[]}
        uploads={[]}
        isUploading={false}
        onFilesSelected={vi.fn()}
        onUpdateImageRoles={vi.fn()}
        onDeleteImage={vi.fn()}
        iconImage={null}
        onIconFilesSelected={vi.fn()}
        onDeleteIcon={vi.fn()}
        competitionStanding={STANDING}
        competitionError=""
        onEnterCompetition={vi.fn()}
      />,
    );

    await act(async () => {
      tabLabelled(container, "Settings")?.click();
    });

    expect(container.textContent).not.toContain("Competitions");
    expect(container.textContent).not.toContain("June round");
    cleanup();
  });
});
