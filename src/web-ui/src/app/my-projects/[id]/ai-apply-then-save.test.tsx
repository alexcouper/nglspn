import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";

import type { Project } from "@/lib/api";
import type { ImportTag, ImportedProject } from "@/lib/project-import";

const { captured } = vi.hoisted(() => ({
  captured: {
    onAiApply: null as null | ((fields: ImportedProject, tags: ImportTag[]) => void),
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => ({ isReady: true, isLoading: false }),
}));
vi.mock("@/hooks/useImageUpload", () => ({
  useImageUpload: () => ({ uploads: [], uploadFiles: vi.fn(), isUploading: false }),
}));
// Stubbed to grab the callback: this asserts what ProjectDetail does with an
// applied reply, not how the panel produces one (ai-import-panel.test.tsx).
vi.mock("./EditProjectContent", () => ({
  EditProjectContent: (props: { onAiApply: typeof captured.onAiApply }) => {
    captured.onAiApply = props.onAiApply;
    return null;
  },
}));
vi.mock("@/lib/api", () => ({
  api: { myProjects: { get: vi.fn(), update: vi.fn() } },
}));

const { api } = await import("@/lib/api");
const { ProjectDetail } = await import("./ProjectDetail");

const PROJECT = {
  id: "project-1",
  slug: "alpha",
  title: "Alpha",
  tagline: "Does a thing",
  description: "A description",
  website_url: "https://alpha.test",
  status: "draft",
  created_at: "2026-06-01T00:00:00Z",
  images: [],
  tags: [{ id: "t-old", name: "Old", slug: "old", color: null }],
  won_competitions: [],
  is_community_tipoff: false,
  competition_standing: { entries: [], opportunities: [] },
} as unknown as Project;

describe("applying an assistant's reply on the edit page", () => {
  it("fills the form without saving, and Save sends the merged listing", async () => {
    vi.mocked(api.myProjects.get).mockResolvedValue(PROJECT);
    vi.mocked(api.myProjects.update).mockResolvedValue(PROJECT);
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<ProjectDetail projectId="project-1" />);
    });

    // Only the tagline and description: title, link and tags stay as they are.
    await act(async () => {
      captured.onAiApply!({ tagline: "Sharper", description: "Rewritten." }, []);
    });

    expect(api.myProjects.update).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Filled in from your assistant");

    await act(async () => {
      [...container.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Save")!.click();
    });

    expect(api.myProjects.update).toHaveBeenCalledWith("project-1", {
      title: "Alpha",
      tagline: "Sharper",
      description: "Rewritten.",
      website_url: "https://alpha.test",
      tag_ids: ["t-old"],
    });

    act(() => root.unmount());
    container.remove();
  });
});
