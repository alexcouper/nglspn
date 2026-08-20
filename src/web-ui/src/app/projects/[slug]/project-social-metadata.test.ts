import { describe, expect, it, vi } from "vitest";

import type { Project } from "@/lib/api";

vi.mock("@/lib/api/server", () => ({
  fetchProject: vi.fn(),
  fetchProjectArticles: vi.fn(),
  getProjectOr404: vi.fn(),
}));

import { fetchProject } from "@/lib/api/server";
import { generateMetadata } from "./page";

function aProject(overrides: Partial<Project> = {}): Project {
  return {
    slug: "naglasupan",
    title: "Naglasúpan",
    tagline: "Byggjum saman",
    description: "A place to build things in public.",
    images: [
      {
        url: "https://cdn.naglasupan.is/projects/abc/main.jpg",
        is_main: true,
        width: 1200,
        height: 630,
      },
    ],
    ...overrides,
  } as unknown as Project;
}

async function metadataFor(project: Project) {
  vi.mocked(fetchProject).mockResolvedValue(project);
  return generateMetadata({ params: Promise.resolve({ slug: "naglasupan" }) });
}

describe("project social card metadata", () => {
  it("puts the project's main image on both cards", async () => {
    const metadata = await metadataFor(aProject());

    expect(metadata.twitter).toMatchObject({
      card: "summary_large_image",
      images: ["https://cdn.naglasupan.is/projects/abc/main.jpg"],
    });
    expect(metadata.openGraph).toMatchObject({
      url: "https://naglasupan.is/projects/naglasupan",
      images: [
        {
          url: "https://cdn.naglasupan.is/projects/abc/main.jpg",
          width: 1200,
          height: 630,
        },
      ],
    });
  });

  it("falls back to the site logo when the project has no images", async () => {
    const metadata = await metadataFor(aProject({ images: [] }));

    expect(metadata.twitter).toMatchObject({
      card: "summary",
      images: ["/icons/app/logo.png"],
    });
    expect(metadata.openGraph).toMatchObject({
      images: [{ url: "/icons/app/logo.png" }],
    });
  });
});
