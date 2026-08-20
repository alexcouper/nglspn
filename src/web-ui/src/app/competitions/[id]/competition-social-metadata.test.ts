import { describe, expect, it, vi } from "vitest";

import type { Competition } from "@/lib/api";

vi.mock("@/lib/api/server", () => ({
  fetchCompetition: vi.fn(),
  ApiNotFoundError: class ApiNotFoundError extends Error {},
}));

import { fetchCompetition } from "@/lib/api/server";
import { generateMetadata } from "./page";

function aCompetition(overrides: Partial<Competition> = {}): Competition {
  return {
    name: "Spínat",
    start_date: "2026-01-01T00:00:00Z",
    submission_deadline: "2026-02-01T00:00:00Z",
    image_url: "https://cdn.naglasupan.is/competitions/spinat.jpg",
    ...overrides,
  } as unknown as Competition;
}

async function metadataFor(competition: Competition) {
  vi.mocked(fetchCompetition).mockResolvedValue(competition);
  return generateMetadata({ params: Promise.resolve({ id: "spinat" }) });
}

describe("competition social card metadata", () => {
  it("puts the competition image on the twitter card", async () => {
    const metadata = await metadataFor(aCompetition());

    expect(metadata.twitter).toMatchObject({
      card: "summary_large_image",
      title: "Spínat",
      images: ["https://cdn.naglasupan.is/competitions/spinat.jpg"],
    });
  });

  it("falls back to the site logo when the competition has no image", async () => {
    const metadata = await metadataFor(aCompetition({ image_url: null }));

    expect(metadata.twitter).toMatchObject({
      card: "summary",
      images: ["/icons/app/logo.png"],
    });
  });
});
