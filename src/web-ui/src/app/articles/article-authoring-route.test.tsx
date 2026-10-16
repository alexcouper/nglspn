import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Project } from "@/lib/api";
import { ArticleAuthoringRoute } from "./ArticleAuthoringRoute";

// Whether the caller is signed in. `useRequireAuth` also owns the redirect to
// /login, which is why the wrapper must not fetch before it says ready.
const { authState } = vi.hoisted(() => ({ authState: { isReady: true } }));

vi.mock("@/hooks/useRequireAuth", () => ({
  useRequireAuth: () => authState,
}));

vi.mock("@/lib/api", () => ({
  api: { projects: { get: vi.fn() } },
}));

// The page under test is the wrapper. Stubbing the authoring page keeps the
// MDXEditor tree, five hooks and their API calls out of these assertions.
vi.mock("./ArticleAuthoringPage", () => ({
  ArticleAuthoringPage: ({
    project,
    articleId,
  }: {
    project: Project;
    articleId: string;
  }) => (
    <div data-testid="authoring-page">
      {project.title} / {articleId}
    </div>
  ),
}));

// After the mocks, so these read the stubs.
const { api } = await import("@/lib/api");
const { ApiRequestError } = await import("@/lib/api/base");

const getProject = api.projects.get as ReturnType<typeof vi.fn>;

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

function notFound() {
  return new ApiRequestError(
    "Request failed",
    { detail: "Project not found" },
    404,
  );
}

// ------------------------------------------------------------------- mounting

async function mountRoute({
  projectRef = "a-project",
  articleId = "article-1",
} = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(
      <ArticleAuthoringRoute projectRef={projectRef} articleId={articleId} />,
    );
  });
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
  getProject.mockResolvedValue(project());
});

describe("ArticleAuthoringRoute", () => {
  it("renders the authoring page for an unapproved project", async () => {
    const { container, unmount } = await mountRoute();

    expect(getProject).toHaveBeenCalledWith("a-project");
    expectAuthoringPage(container, "A project / article-1");
    unmount();
  });

  it("shows the skeleton while the project is in flight", async () => {
    getProject.mockReturnValue(new Promise(() => {}));

    const { container, unmount } = await mountRoute();

    expectSkeleton(container);
    expectNoAuthoringPage(container);
    unmount();
  });

  it("shows an in-page error with a way back when the project 404s", async () => {
    getProject.mockRejectedValue(notFound());

    const { container, unmount } = await mountRoute();

    expect(container.textContent).toContain("Couldn't open this project");
    expect(container.querySelector("[role='alert']")?.textContent).toBe(
      "Project not found",
    );
    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "/my-projects",
    );
    expectNoAuthoringPage(container);
    unmount();
  });

  it("does not request the project before auth is ready", async () => {
    authState.isReady = false;

    const { container, unmount } = await mountRoute();

    expect(getProject).not.toHaveBeenCalled();
    expectSkeleton(container);
    unmount();
  });
});
