import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { PublicUserProfile, UserArticle, UserProject } from "@/lib/api";

const { authState } = vi.hoisted(() => ({
  authState: { value: { user: null as { id: string } | null } },
}));

vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));
vi.mock("@/lib/api", () => ({
  api: {
    users: {
      getPublicProfile: vi.fn(),
      listProjects: vi.fn(),
      listArticles: vi.fn(),
    },
  },
  ApiRequestError: class ApiRequestError extends Error {
    constructor(
      message: string,
      public body: Record<string, unknown>,
      public status: number,
    ) {
      super(message);
    }
  },
}));

const { api, ApiRequestError } = await import("@/lib/api");
const { ProfileView, joinedLine } = await import("./page");

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  // Let the chained list requests land.
  await act(async () => {});
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- factories

const USER_ID = "user-1";

function profile(overrides: Partial<PublicUserProfile> = {}): PublicUserProfile {
  return {
    id: USER_ID,
    first_name: "Sigrún",
    last_name: "Helgadóttir",
    info: "Landscape architect in **Vesturbær**.",
    is_system_user: false,
    avatar_url: null,
    created_at: "2025-03-12T10:00:00Z",
    ...overrides,
  };
}

function project(overrides: Partial<UserProject> = {}): UserProject {
  return {
    id: "project-1",
    slug: "garden",
    title: "Vesturbær Community Garden",
    tagline: "Shared plots",
    category_name: "Environment",
    main_image_thumb_url: null,
    role: "owner",
    ...overrides,
  };
}

function article(overrides: Partial<UserArticle> = {}): UserArticle {
  return {
    id: "article-1",
    title: "Spring planting day",
    summary: "Forty people, eleven plots.",
    slug: "spring-planting",
    published_at: "2026-05-14T10:00:00Z",
    channel: { id: "channel-1", name: "Updates" },
    project: { id: "project-1", slug: "garden", title: "Vesturbær Community Garden" },
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  };
}

function givenProfile(
  p: PublicUserProfile,
  projects: UserProject[] = [],
  articles: UserArticle[] = [],
) {
  vi.mocked(api.users.getPublicProfile).mockResolvedValue(p);
  vi.mocked(api.users.listProjects).mockResolvedValue(projects);
  vi.mocked(api.users.listArticles).mockResolvedValue(articles);
}

// ---------------------------------------------------------------- helpers

function text(container: HTMLElement, selector: string): string {
  return container.querySelector(selector)?.textContent ?? "";
}

function editProfileLink(container: HTMLElement) {
  return [...container.querySelectorAll("a")].find((a) =>
    a.textContent?.includes("Edit profile"),
  );
}

function roleChips(container: HTMLElement): string[] {
  return [...container.querySelectorAll('[data-testid="project-tile-role"]')].map(
    (el) => el.textContent ?? "",
  );
}

// ---------------------------------------------------------------- the tests

describe("the public profile page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.value = { user: null };
  });

  it("shows who the person is and what they have done", async () => {
    givenProfile(
      profile(),
      [project(), project({ id: "project-2", slug: "river", title: "Riverbank", role: "tipster" })],
      [article()],
    );

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(text(container, "h1")).toBe("Sigrún Helgadóttir");
    expect(text(container, '[data-testid="profile-meta"]')).toBe(
      `${joinedLine("2025-03-12T10:00:00Z")} · 2 projects · 1 article`,
    );
    expect(container.querySelector('[data-testid="profile-about"] strong')?.textContent).toBe(
      "Vesturbær",
    );
    expect(roleChips(container)).toEqual(["Owner", "Tipped off"]);
    expect(
      container.querySelector('a[href="/projects/garden/articles/spring-planting"]'),
    ).not.toBeNull();
    expect(container.textContent).toContain("Vesturbær Community Garden · Updates");
    cleanup();
  });

  it("says so when there is nothing yet, and counts zero", async () => {
    givenProfile(profile());

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(container.textContent).toContain("No projects yet.");
    expect(container.textContent).toContain("No articles yet.");
    expect(text(container, '[data-testid="profile-meta"]')).toContain("0 projects · 0 articles");
    cleanup();
  });

  it("shows a failed list as an error, not as nothing yet", async () => {
    vi.mocked(api.users.getPublicProfile).mockResolvedValue(profile());
    vi.mocked(api.users.listProjects).mockRejectedValue(new Error("Service Unavailable"));
    vi.mocked(api.users.listArticles).mockResolvedValue([article()]);

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(container.querySelector('[data-testid="profile-projects-error"]')).not.toBeNull();
    expect(container.textContent).not.toContain("No projects yet.");
    expect(text(container, '[data-testid="profile-meta"]')).toBe(
      `${joinedLine("2025-03-12T10:00:00Z")} · 1 article`,
    );
    cleanup();
  });

  it("renders User not found on a 404 and asks for nothing else", async () => {
    vi.mocked(api.users.getPublicProfile).mockRejectedValue(
      new ApiRequestError("Not found", {}, 404),
    );

    const { container, unmount: cleanup } = await mount(<ProfileView id="nobody" />);

    expect(text(container, "h1")).toBe("User not found");
    expect(api.users.listProjects).not.toHaveBeenCalled();
    expect(api.users.listArticles).not.toHaveBeenCalled();
    cleanup();
  });

  it("offers Edit profile only on the viewer's own page", async () => {
    givenProfile(profile());

    authState.value = { user: { id: USER_ID } };
    const own = await mount(<ProfileView id={USER_ID} />);
    expect(editProfileLink(own.container)?.getAttribute("href")).toBe("/profile");
    own.unmount();

    authState.value = { user: { id: "someone-else" } };
    const other = await mount(<ProfileView id={USER_ID} />);
    expect(editProfileLink(other.container)).toBeUndefined();
    other.unmount();

    authState.value = { user: null };
    const anonymous = await mount(<ProfileView id={USER_ID} />);
    expect(editProfileLink(anonymous.container)).toBeUndefined();
    anonymous.unmount();
  });

  it("drops images from the About markdown but keeps links", async () => {
    givenProfile(
      profile({
        info: "Hello ![x](https://example.com/a.png) and [site](https://example.is)",
      }),
    );

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    const about = container.querySelector('[data-testid="profile-about"]')!;
    expect(about.querySelector("img")).toBeNull();
    expect(about.querySelector('a[href="https://example.is"]')).not.toBeNull();
    cleanup();
  });
});
