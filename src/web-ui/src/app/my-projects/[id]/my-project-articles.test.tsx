import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { ArticleListItem, Channel } from "@/lib/api";
import { MyProjectArticles } from "./MyProjectArticles";

// One router object for the whole file, so a re-render never hands the
// component a different identity than the assertions hold.
const { push, router } = vi.hoisted(() => {
  const push = vi.fn();
  return { push, router: { push, replace: vi.fn() } };
});

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/lib/api", () => ({
  api: {
    channels: { list: vi.fn() },
    articles: { list: vi.fn(), create: vi.fn() },
  },
}));

const { api } = await import("@/lib/api");

// From "@/lib/api/base", never the mocked barrel: describeApiError narrows with
// `instanceof`, and a second copy of the class would fall through to the
// fallback sentence.
const { ApiRequestError } = await import("@/lib/api/base");

const channels = api.channels.list as ReturnType<typeof vi.fn>;
const articles = api.articles as unknown as Record<
  "list" | "create",
  ReturnType<typeof vi.fn>
>;

// --------------------------------------------------------------- factories

function channel(overrides: Partial<Channel> = {}): Channel {
  return { id: "channel-1", name: "Updates", ...overrides } as Channel;
}

function articleListItem(
  overrides: Partial<ArticleListItem> = {},
): ArticleListItem {
  return {
    id: "article-1",
    title: "A headline",
    summary: "",
    slug: "a-headline",
    state: "published",
    published_at: "2026-08-01T10:00:00Z",
    global_visibility: "auto",
    channel: { id: "channel-1", name: "Updates" },
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  } as unknown as ArticleListItem;
}

// ---------------------------------------------------------------- mounting

async function mountArticles(projectSlugOrId = "a-project") {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  await act(async () => {
    root.render(<MyProjectArticles projectSlugOrId={projectSlugOrId} />);
  });

  return {
    container,
    newArticleButton: () => findNewArticleButton(container),
    click: async (el: HTMLElement) => {
      await act(async () => {
        el.click();
      });
    },
    errorText: () =>
      container.querySelector('[role="alert"]')?.textContent ?? null,
    unmount: async () => {
      await act(async () => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function findNewArticleButton(container: HTMLElement): HTMLButtonElement {
  const button = [...container.querySelectorAll("button")].find((b) =>
    b.textContent?.includes("New article"),
  );
  if (!button) throw new Error("no New article button rendered");
  return button;
}

// ---------------------------------------------------------------- the tests

beforeEach(() => {
  vi.clearAllMocks();
  channels.mockResolvedValue([channel()]);
  articles.list.mockResolvedValue([articleListItem()]);
  articles.create.mockResolvedValue({ id: "new-article-1" });
});

describe("starting a new article", () => {
  it("creates the draft and opens its editor", async () => {
    const harness = await mountArticles();

    await harness.click(harness.newArticleButton());

    expect(articles.create).toHaveBeenCalledWith("a-project", {
      channel_id: "channel-1",
      title: "",
      body: "",
    });
    expect(push).toHaveBeenCalledWith(
      "/projects/a-project/articles/edit/new-article-1",
    );

    await harness.unmount();
  });

  it("creates one draft however fast the button is clicked twice", async () => {
    let release: (value: { id: string }) => void = () => {};
    articles.create.mockReturnValue(
      new Promise<{ id: string }>((resolve) => {
        release = resolve;
      }),
    );
    const harness = await mountArticles();

    const button = harness.newArticleButton();
    await harness.click(button);
    await harness.click(button);

    expect(articles.create).toHaveBeenCalledOnce();

    await act(async () => {
      release({ id: "new-article-1" });
    });
    await harness.unmount();
  });

  it("cannot be started before the channel it would go in is known", async () => {
    channels.mockReturnValue(new Promise(() => {}));
    const harness = await mountArticles();

    expect(harness.newArticleButton().disabled).toBe(true);

    await harness.unmount();
  });

  it("stays on the list and says why when the draft cannot be created", async () => {
    articles.create.mockRejectedValue(
      new ApiRequestError(
        "Request failed",
        { detail: "Channel not found on this project" },
        404,
      ),
    );
    const harness = await mountArticles();

    await harness.click(harness.newArticleButton());

    expect(push).not.toHaveBeenCalled();
    expect(harness.errorText()).toContain("Channel not found on this project");
    expect(harness.newArticleButton().disabled).toBe(false);

    await harness.unmount();
  });

  it("is not offered to a project with no channel to publish into", async () => {
    channels.mockResolvedValue([]);
    const harness = await mountArticles();

    expect(harness.newArticleButton().disabled).toBe(true);

    await harness.unmount();
  });
});

describe("the article list", () => {
  it("loads articles and channels together rather than one after the other", async () => {
    const harness = await mountArticles();

    expect(articles.list).toHaveBeenCalledOnce();
    expect(channels).toHaveBeenCalledOnce();

    await harness.unmount();
  });

  it("still lists articles when the channel lookup fails", async () => {
    channels.mockRejectedValue(new Error("channels are down"));
    const harness = await mountArticles();

    expect(harness.container.textContent).toContain("A headline");

    await harness.unmount();
  });
});
