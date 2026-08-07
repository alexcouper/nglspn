import { beforeEach, describe, expect, it, vi } from "vitest";
import { StrictMode, act } from "react";
import { createRoot } from "react-dom/client";
import type { Article, Channel, Project, ProjectImage } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";
import { useArticleDraft } from "./useArticleDraft";

// One router object for the whole file. The hook lists `router` in the deps of
// its load effect, so handing back a fresh object per render would re-run the
// load on every state update.
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  const push = vi.fn();
  return { replace, router: { replace, push } };
});

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/lib/api", () => ({
  api: {
    channels: { list: vi.fn() },
    articles: {
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      publish: vi.fn(),
    },
  },
}));

// After the mock, so the tests read the stubs rather than the real client.
const { api } = await import("@/lib/api");

const channels = api.channels.list as ReturnType<typeof vi.fn>;
const articles = api.articles as unknown as Record<
  "get" | "create" | "update" | "delete" | "publish",
  ReturnType<typeof vi.fn>
>;

// --------------------------------------------------------------- factories

function channel(overrides: Partial<Channel> = {}): Channel {
  return { id: "channel-1", name: "Releases", ...overrides } as Channel;
}

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "project-1",
    slug: "a-project",
    title: "A project",
    ...overrides,
  } as unknown as Project;
}

function image(overrides: Partial<ProjectImage> = {}): ProjectImage {
  return {
    id: "image-1",
    url: "https://cdn.example/one.png",
    original_filename: "one.png",
    width: 1600,
    height: 900,
    variants: [],
    ...overrides,
  } as unknown as ProjectImage;
}

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-1",
    project: { id: "project-1", slug: "a-project", title: "A project" },
    channel: channel(),
    author: null,
    title: "",
    body: "",
    summary: "",
    summary_display: "",
    listing_image_id: null,
    listing_image_url: null,
    listing_image: null,
    listing_crop: null,
    listing_image_mode: "auto",
    images: [],
    slug: null,
    state: "draft",
    published_at: null,
    global_visibility: "auto",
    is_globally_visible: false,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  } as Article;
}

const CROP: CropRect = { x: 0.1, y: 0.2, w: 0.4, h: 0.225, ratio: 16 / 9 };

const PROJECT = project();

// ---------------------------------------------------------------- mounting

type Draft = ReturnType<typeof useArticleDraft>;

function Harness({
  articleId,
  report,
}: {
  articleId?: string;
  report: (draft: Draft) => void;
}) {
  report(useArticleDraft({ project: PROJECT, articleId }));
  return null;
}

async function mountDraft({
  articleId,
  strict = false,
}: { articleId?: string; strict?: boolean } = {}) {
  let latest: Draft | null = null;
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const element = (
    <Harness
      articleId={articleId}
      report={(draft) => {
        latest = draft;
      }}
    />
  );

  await act(async () => {
    root.render(strict ? <StrictMode>{element}</StrictMode> : element);
  });

  return {
    // A getter, not a snapshot: every render replaces the object.
    draft: () => latest!,
    act: async (fn: () => void | Promise<void>) => {
      await act(async () => {
        await fn();
      });
    },
    unmount: async () => {
      await act(async () => {
        root.unmount();
      });
      container.remove();
    },
  };
}

// ---------------------------------------------------------------- the tests

beforeEach(() => {
  vi.clearAllMocks();
  channels.mockResolvedValue([channel()]);
  articles.get.mockResolvedValue(article());
  articles.create.mockResolvedValue(article());
  articles.update.mockImplementation(async () => article());
  articles.delete.mockResolvedValue(undefined);
  articles.publish.mockResolvedValue(undefined);
});

describe("opening /new", () => {
  it("creates a draft up front and swaps the URL to its edit route", async () => {
    const harness = await mountDraft();

    expect(articles.create).toHaveBeenCalledOnce();
    expect(replace).toHaveBeenCalledWith(
      "/projects/a-project/articles/edit/article-1",
    );

    await harness.unmount();
  });

  it("creates one draft per visit when effects run twice", async () => {
    const harness = await mountDraft({ strict: true });

    expect(articles.create).toHaveBeenCalledOnce();

    await harness.unmount();
  });

  it("leaves the draft it is navigating to alone", async () => {
    const harness = await mountDraft();

    await harness.unmount();

    expect(articles.delete).not.toHaveBeenCalled();
  });
});

describe("a load that fails", () => {
  it("reports the error rather than leaving the page with nothing", async () => {
    articles.get.mockRejectedValue(new Error("Article not found"));

    const harness = await mountDraft({ articleId: "article-1" });

    expect(harness.draft().error).toBe("Article not found");
    expect(harness.draft().isLoading).toBe(false);
    expect(harness.draft().form).toBeNull();

    await harness.unmount();
  });
});

describe("choosing a listing image", () => {
  it("shows an image uploaded in the wizard before any save", async () => {
    const uploaded = image({ id: "fresh-upload" });
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().chooseListingImage(uploaded, CROP);
    });

    expect(harness.draft().listingImage?.id).toBe("fresh-upload");
    expect(harness.draft().images).toEqual([uploaded]);
    expect(harness.draft().form?.listing_image_mode).toBe("chosen");

    await harness.unmount();
  });

  it("does not list an already-known image twice", async () => {
    const known = image();
    articles.get.mockResolvedValue(article({ images: [known] }));
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().chooseListingImage(known, CROP);
    });

    expect(harness.draft().images).toHaveLength(1);

    await harness.unmount();
  });

  it("falls back to the saved image the server resolved for `auto`", async () => {
    const resolved = image({ id: "auto-resolved" });
    articles.get.mockResolvedValue(
      article({
        listing_image_id: "auto-resolved",
        listing_image: resolved,
        images: [],
      }),
    );

    const harness = await mountDraft({ articleId: "article-1" });

    expect(harness.draft().listingImage?.id).toBe("auto-resolved");

    await harness.unmount();
  });

  it("clears the image and says so when it is removed", async () => {
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().removeListingImage();
    });

    expect(harness.draft().listingImage).toBeNull();
    expect(harness.draft().form?.listing_image_mode).toBe("none");

    await harness.unmount();
  });
});

describe("the untouched-draft sweep", () => {
  it("deletes a draft nobody wrote anything into", async () => {
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.unmount();

    expect(articles.delete).toHaveBeenCalledWith("a-project", "article-1");
  });

  it("keeps a draft whose headline was typed but not saved", async () => {
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().updateForm({ title: "A headline" });
    });
    await harness.unmount();

    expect(articles.delete).not.toHaveBeenCalled();
  });

  it("keeps a draft whose body was typed but not saved", async () => {
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().handleBodyChange("Some prose.");
    });
    await harness.unmount();

    expect(articles.delete).not.toHaveBeenCalled();
  });

  it("keeps a draft that already has content", async () => {
    articles.get.mockResolvedValue(article({ title: "Saved headline" }));
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.unmount();

    expect(articles.delete).not.toHaveBeenCalled();
  });
});

describe("saving", () => {
  it("persists the live body rather than the form's stale copy", async () => {
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(async () => {
      harness.draft().handleBodyChange("Typed after load.");
      await harness.draft().save();
    });

    expect(articles.update).toHaveBeenCalledWith(
      "a-project",
      "article-1",
      expect.objectContaining({ body: "Typed after load." }),
    );

    await harness.unmount();
  });

  it("adopts the image ids the server resolved for `auto`", async () => {
    articles.update.mockResolvedValue(
      article({
        listing_image_id: "server-picked",
        listing_image_mode: "auto",
      }),
    );
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(async () => {
      await harness.draft().save();
    });

    expect(harness.draft().form?.listing_image_id).toBe("server-picked");

    await harness.unmount();
  });

  it("surfaces a failure instead of claiming the draft was saved", async () => {
    articles.update.mockRejectedValue(new Error("Service unavailable"));
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(async () => {
      await harness.draft().save();
    });

    expect(harness.draft().error).toBe("Service unavailable");
    expect(harness.draft().successMessage).toBe("");

    await harness.unmount();
  });
});

describe("unsaved changes", () => {
  it("is clean on a freshly loaded article", async () => {
    articles.get.mockResolvedValue(article({ title: "Saved", body: "Body." }));
    const harness = await mountDraft({ articleId: "article-1" });

    expect(harness.draft().isDirty()).toBe(false);

    await harness.unmount();
  });

  it("notices a body that only exists in the editor", async () => {
    articles.get.mockResolvedValue(article({ title: "Saved", body: "Body." }));
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().handleBodyChange("Body, extended.");
    });

    expect(harness.draft().isDirty()).toBe(true);

    await harness.unmount();
  });

  it("notices an edited form field", async () => {
    articles.get.mockResolvedValue(article({ title: "Saved", body: "Body." }));
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(() => {
      harness.draft().updateForm({ summary: "A standfirst." });
    });

    expect(harness.draft().isDirty()).toBe(true);

    await harness.unmount();
  });

  it("is clean again once the save has come back", async () => {
    const saved = article({ title: "Saved", body: "Body, extended." });
    articles.get.mockResolvedValue(article({ title: "Saved", body: "Body." }));
    articles.update.mockResolvedValue(saved);
    const harness = await mountDraft({ articleId: "article-1" });

    await harness.act(async () => {
      harness.draft().handleBodyChange("Body, extended.");
      await harness.draft().save();
    });

    expect(harness.draft().isDirty()).toBe(false);

    await harness.unmount();
  });
});
