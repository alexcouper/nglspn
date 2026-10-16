import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { OwnArticle, UserArticle, UserProfile, UserProject } from "@/lib/api";

const { authState, router } = vi.hoisted(() => ({
  authState: {
    value: {
      user: null as { id: string } | null,
      isAuthenticated: false,
      isLoading: false,
    },
  },
  router: { push: vi.fn() },
}));

vi.mock("@/contexts/auth", () => ({ useAuth: () => authState.value }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/users/user-1",
}));
vi.mock("@/lib/api", () => ({
  api: {
    users: {
      getPublicProfile: vi.fn(),
      listProjects: vi.fn(),
      listArticles: vi.fn(),
    },
    articles: {
      listOwn: vi.fn(),
      createOwn: vi.fn(),
    },
    follows: {
      followUser: vi.fn(),
      unfollowUser: vi.fn(),
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
const { ProfileView, joinedMonth } = await import("./page");

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

function profile(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    id: USER_ID,
    first_name: "Sigrún",
    last_name: "Helgadóttir",
    info: "Landscape architect in **Vesturbær**.",
    is_system_user: false,
    avatar_url: null,
    created_at: "2025-03-12T10:00:00Z",
    is_followed: false,
    ...overrides,
  };
}

function ownArticle(overrides: Partial<OwnArticle> = {}): OwnArticle {
  return {
    ...article(),
    id: "own-1",
    title: "Why I keep a notebook",
    slug: null,
    published_at: null,
    channel: null,
    project: null,
    state: "draft",
    global_visibility: "auto",
    is_globally_visible: false,
    ...overrides,
  } as OwnArticle;
}

function signedInAs(id: string) {
  authState.value = { user: { id }, isAuthenticated: true, isLoading: false };
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
  p: UserProfile,
  projects: UserProject[] = [],
  articles: UserArticle[] = [],
  own: OwnArticle[] = [],
) {
  vi.mocked(api.users.getPublicProfile).mockResolvedValue(p);
  vi.mocked(api.users.listProjects).mockResolvedValue(projects);
  vi.mocked(api.users.listArticles).mockResolvedValue(articles);
  vi.mocked(api.articles.listOwn).mockResolvedValue(own);
}

function buttonLabelled(container: HTMLElement, label: string) {
  return [...container.querySelectorAll("button")].find((b) => b.textContent?.trim() === label);
}

function badges(container: HTMLElement): string[] {
  return [...container.querySelectorAll('[data-testid="article-badge"]')].map(
    (el) => el.textContent ?? "",
  );
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
    authState.value = { user: null, isAuthenticated: false, isLoading: false };
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
      `Joined ${joinedMonth("2025-03-12T10:00:00Z")} · 2 projects · 1 article`,
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
      `Joined ${joinedMonth("2025-03-12T10:00:00Z")} · 1 article`,
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

    signedInAs(USER_ID);
    const own = await mount(<ProfileView id={USER_ID} />);
    expect(editProfileLink(own.container)?.getAttribute("href")).toBe("/profile");
    own.unmount();

    signedInAs("someone-else");
    const other = await mount(<ProfileView id={USER_ID} />);
    expect(editProfileLink(other.container)).toBeUndefined();
    other.unmount();

    authState.value = { user: null, isAuthenticated: false, isLoading: false };
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


describe("following and writing from the profile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.value = { user: null, isAuthenticated: false, isLoading: false };
  });

  it("offers Follow to a signed-in visitor and reports the server's answer", async () => {
    givenProfile(profile({ is_followed: true }));
    signedInAs("someone-else");

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(buttonLabelled(container, "Following")).toBeDefined();
    expect(buttonLabelled(container, "Write article")).toBeUndefined();
    cleanup();
  });

  it("sends an anonymous visitor who presses Follow to log in", async () => {
    givenProfile(profile());

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    const follow = buttonLabelled(container, "Follow");
    expect(follow).toBeDefined();
    await act(async () => {
      follow!.click();
    });
    expect(router.push).toHaveBeenCalledWith("/login?next=%2Fusers%2Fuser-1");
    cleanup();
  });

  it("shows no Follow button on the viewer's own page", async () => {
    givenProfile(profile());
    signedInAs(USER_ID);

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(buttonLabelled(container, "Follow")).toBeUndefined();
    cleanup();
  });

  it("lists the owner's own articles with their badges and opens the editor", async () => {
    givenProfile(profile(), [], [], [
      ownArticle(),
      ownArticle({
        id: "own-2",
        title: "Held back",
        state: "published",
        slug: "held-back",
        published_at: "2026-06-01T10:00:00Z",
        global_visibility: "pending",
      }),
      ownArticle({
        id: "own-3",
        title: "Out there",
        state: "published",
        slug: "out-there",
        published_at: "2026-05-01T10:00:00Z",
        is_globally_visible: true,
      }),
    ]);
    signedInAs(USER_ID);

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(badges(container)).toEqual(["Draft", "Pending review", "Published"]);
    expect(container.querySelector('a[href="/articles/edit/own-1"]')).not.toBeNull();
    expect(api.users.listArticles).not.toHaveBeenCalled();
    cleanup();
  });

  it("creates a draft and opens the editor on Write article", async () => {
    givenProfile(profile());
    signedInAs(USER_ID);
    vi.mocked(api.articles.createOwn).mockResolvedValue({ id: "new-1" } as never);

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    await act(async () => {
      buttonLabelled(container, "Write article")!.click();
    });
    expect(router.push).toHaveBeenCalledWith("/articles/edit/new-1");
    cleanup();
  });

  it("shows a visitor an author-owned article under the author's name and address", async () => {
    givenProfile(profile(), [], [
      article({ id: "a-own", slug: "notebook", project: null, channel: { id: "c", name: "Articles" } }),
    ]);

    const { container, unmount: cleanup } = await mount(<ProfileView id={USER_ID} />);

    expect(container.querySelector('a[href="/users/user-1/articles/notebook"]')).not.toBeNull();
    expect(container.textContent).toContain("Sigrún Helgadóttir");
    expect(container.textContent).not.toContain("Articles ·");
    cleanup();
  });
});
