import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Article, Project } from "@/lib/api";
import { ArticleAuthoringRoute } from "./ArticleAuthoringRoute";

// Whether the caller is signed in. `useRequireAuth` also owns the redirect to
// /login, which is why the wrapper must not fetch before it says ready.
const { authState } = vi.hoisted(() => ({ authState: { isReady: true } }));

vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => authState,
}));

vi.mock("@/lib/api", () => ({
  api: { projects: { get: vi.fn() }, articles: { get: vi.fn() } },
}));

// The page under test is the wrapper. Stubbing the authoring page keeps the
// MDXEditor tree, five hooks and their API calls out of these assertions.
vi.mock("./ArticleAuthoringPage", () => ({
  ArticleAuthoringPage: ({
    project,
    initialArticle,
  }: {
    project: Project | null;
    initialArticle: Article;
  }) => (
    <div data-testid="authoring-page">
      {project ? project.title : "(own)"} / {initialArticle.id}
    </div>
  ),
}));

// After the mocks, so these read the stubs.
const { api } = await import("@/lib/api");
const { ApiRequestError } = await import("@/lib/api/base");

const getProject = api.projects.get as ReturnType<typeof vi.fn>;
const getArticle = api.articles.get as ReturnType<typeof vi.fn>;

// ------------------------------------------------------------------ factories

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "project-1",
    slug: "a-project",
    title: "A project",
    status: "draft",
    contributors: [],
    ...overrides,
  } as unknown as Project;
}

function projectArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-1",
    project: { id: "project-1", slug: "a-project", title: "A project" },
    channel: { id: "channel-1", name: "Updates" },
    author: null,
    ...overrides,
  } as unknown as Article;
}

function ownArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-2",
    project: null,
    channel: null,
    author: { id: "user-1", first_name: "Ada", last_name: "Lovelace" },
    ...overrides,
  } as unknown as Article;
}

function notFound() {
  return new ApiRequestError(
    "Request failed",
    { detail: "Article not found" },
    404,
  );
}

// ------------------------------------------------------------------- mounting

async function mountRoute({ articleId = "article-1" } = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<ArticleAuthoringRoute articleId={articleId} />);
  });
  // The project request follows the article's; let it land.
  await act(async () => {});
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- expectations

function expectAuthoringPage(container: HTMLElement, text: string) {
  const page = container.querySelector("[data-testid='authoring-page']");
  expect(page?.textContent).toBe(text);
}

function expectNoAuthoringPage(container: HTMLElement) {
  expect(container.querySelector("[data-testid='authoring-page']")).toBeNull();
}

function expectSkeleton(container: HTMLElement) {
  expect(container.querySelector(".skeleton")).not.toBeNull();
}

// ------------------------------------------------------------------ the tests

beforeEach(() => {
  vi.clearAllMocks();
  authState.isReady = true;
  getArticle.mockResolvedValue(projectArticle());
  getProject.mockResolvedValue(project());
});

describe("ArticleAuthoringRoute", () => {
  it("loads the article first, then its project, for a project article", async () => {
    const { container, unmount } = await mountRoute();

    expect(getArticle).toHaveBeenCalledWith("article-1");
    expect(getProject).toHaveBeenCalledWith("a-project");
    expectAuthoringPage(container, "A project / article-1");
    unmount();
  });

  it("opens an author-owned article without asking for any project", async () => {
    getArticle.mockResolvedValue(ownArticle());

    const { container, unmount } = await mountRoute({ articleId: "article-2" });

    expect(getProject).not.toHaveBeenCalled();
    expectAuthoringPage(container, "(own) / article-2");
    unmount();
  });

  it("shows the skeleton while the article is in flight", async () => {
    getArticle.mockReturnValue(new Promise(() => {}));

    const { container, unmount } = await mountRoute();

    expectSkeleton(container);
    expectNoAuthoringPage(container);
    unmount();
  });

  it("shows an in-page error with a way back when the article 404s", async () => {
    getArticle.mockRejectedValue(notFound());

    const { container, unmount } = await mountRoute();

    expect(container.textContent).toContain("Couldn't open this article");
    expect(container.querySelector("[role='alert']")?.textContent).toBe(
      "Article not found",
    );
    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "/my-projects",
    );
    expectNoAuthoringPage(container);
    unmount();
  });

  it("does not request the article before auth is ready", async () => {
    authState.isReady = false;

    const { container, unmount } = await mountRoute();

    expect(getArticle).not.toHaveBeenCalled();
    expectSkeleton(container);
    unmount();
  });
});
