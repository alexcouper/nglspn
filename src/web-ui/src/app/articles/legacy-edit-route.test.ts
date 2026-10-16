import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ redirect: vi.fn() }));

const { redirect } = await import("next/navigation");
const { default: LegacyEditArticlePage } = await import(
  "@/app/projects/[slug]/articles/edit/[articleId]/page"
);

describe("the old editor route", () => {
  it("redirects to the editor at /articles/edit/{id}", async () => {
    await LegacyEditArticlePage({
      params: Promise.resolve({ slug: "a-project", articleId: "article-1" }),
    });

    expect(redirect).toHaveBeenCalledWith("/articles/edit/article-1");
  });
});
