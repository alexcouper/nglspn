import { describe, expect, it, vi } from "vitest";

import type { Article } from "@/lib/api";

vi.mock("@/lib/api/server", () => ({
  fetchArticleBySlug: vi.fn(),
  getProjectOr404: vi.fn(),
  ApiNotFoundError: class ApiNotFoundError extends Error {},
}));

import { fetchArticleBySlug } from "@/lib/api/server";
import { generateMetadata } from "./page";

function anArticle(overrides: Partial<Article> = {}): Article {
  return {
    title: "Voting Changes - Schulze",
    summary: "Why the ranking page was rebuilt around the Schulze method.",
    summary_display: "The ranking page suffered from a couple of biases.",
    listing_image_url: "https://cdn.naglasupan.is/projects/abc/ballot-box.jpg",
    project: { title: "naglasúpan", slug: "naglasupan" },
    ...overrides,
  } as unknown as Article;
}

async function metadataFor(article: Article) {
  vi.mocked(fetchArticleBySlug).mockResolvedValue(article);
  return generateMetadata({
    params: Promise.resolve({
      slug: "naglasupan",
      articleSlug: "voting-changes-schulze",
    }),
  });
}

describe("article social card metadata", () => {
  it("puts the article's listing image on the twitter card", async () => {
    const metadata = await metadataFor(anArticle());

    expect(metadata.twitter).toMatchObject({
      images: ["https://cdn.naglasupan.is/projects/abc/ballot-box.jpg"],
    });
  });

  it("asks for a large twitter card so scrapers do not render a thumbnail", async () => {
    const metadata = await metadataFor(anArticle());

    expect(metadata.twitter).toMatchObject({ card: "summary_large_image" });
  });

  it("titles the twitter card with the article, not the site name", async () => {
    const metadata = await metadataFor(anArticle());

    expect(metadata.twitter).toMatchObject({
      title: "Voting Changes - Schulze",
      description: "Why the ranking page was rebuilt around the Schulze method.",
    });
  });

  it("falls back to the site logo when the article has no listing image", async () => {
    const metadata = await metadataFor(anArticle({ listing_image_url: null }));

    expect(metadata.twitter).toMatchObject({
      card: "summary",
      images: ["/icons/app/logo.png"],
    });
    expect(metadata.openGraph).toMatchObject({
      images: [{ url: "/icons/app/logo.png" }],
    });
  });

  it("keeps the article image on the open graph card", async () => {
    const metadata = await metadataFor(anArticle());

    expect(metadata.openGraph).toMatchObject({
      type: "article",
      images: [
        {
          url: "https://cdn.naglasupan.is/projects/abc/ballot-box.jpg",
          alt: "Voting Changes - Schulze",
        },
      ],
    });
  });
});
