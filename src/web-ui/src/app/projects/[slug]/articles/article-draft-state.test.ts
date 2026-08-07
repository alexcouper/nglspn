import { describe, expect, it } from "vitest";
import type { Article } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";
import {
  type ArticleFormFields,
  fieldsFromArticle,
  hasUnsavedChanges,
  shouldDiscardDraft,
} from "./articleDraftState";

// --------------------------------------------------------------- factories

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-1",
    project: { id: "project-1", slug: "a-project", title: "A project" },
    channel: { id: "channel-1", name: "Releases" },
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

function image(id = "image-1") {
  return {
    id,
    url: `https://cdn.example/${id}.png`,
    original_filename: `${id}.png`,
    width: 1600,
    height: 900,
    variants: [],
  } as unknown as Article["images"][number];
}

const CROP: CropRect = { x: 0.1, y: 0.2, w: 0.4, h: 0.225, ratio: 16 / 9 };

// The article the author is looking at, and the fields as loaded from it.
function loaded(overrides: Partial<Article> = {}) {
  const saved = article(overrides);
  return { article: saved, fields: fieldsFromArticle(saved) };
}

// ------------------------------------------------------------ the fields

describe("fieldsFromArticle", () => {
  it("copies the editable fields and leaves the body out of them", () => {
    const fields = fieldsFromArticle(
      article({
        title: "A headline",
        body: "Prose the editor holds.",
        summary: "A standfirst.",
        listing_image_id: "image-1",
        listing_crop: CROP,
        listing_image_mode: "chosen",
      }),
    );

    expect(fields).toEqual({
      title: "A headline",
      channel_id: "channel-1",
      summary: "A standfirst.",
      listing_image_id: "image-1",
      listing_crop: CROP,
      listing_image_mode: "chosen",
    } satisfies ArticleFormFields);
  });
});

// ----------------------------------------------------------- unsaved work

describe("hasUnsavedChanges", () => {
  function isDirtyAfter(patch: Partial<ArticleFormFields>): boolean {
    const { article: saved, fields } = loaded({
      title: "Saved",
      body: "Body.",
      summary: "Standfirst.",
    });
    return hasUnsavedChanges(saved, { ...fields, ...patch }, saved.body);
  }

  it("is clean on a freshly loaded article", () => {
    const { article: saved, fields } = loaded({
      title: "Saved",
      body: "Body.",
    });

    expect(hasUnsavedChanges(saved, fields, saved.body)).toBe(false);
  });

  it("notices a body that only exists in the editor", () => {
    const { article: saved, fields } = loaded({
      title: "Saved",
      body: "Body.",
    });

    expect(hasUnsavedChanges(saved, fields, "Body, extended.")).toBe(true);
  });

  it.each([
    ["title", { title: "Retitled" }],
    ["summary", { summary: "A new standfirst." }],
    ["channel", { channel_id: "channel-2" }],
    ["listing image", { listing_image_id: "image-1" }],
    ["listing image mode", { listing_image_mode: "none" as const }],
    ["listing crop", { listing_crop: CROP }],
  ])("notices an edited %s", (_field, patch) => {
    expect(isDirtyAfter(patch)).toBe(true);
  });

  it("ignores a crop redrawn to the same rectangle", () => {
    const { article: saved, fields } = loaded({ listing_crop: CROP });

    expect(
      hasUnsavedChanges(saved, { ...fields, listing_crop: { ...CROP } }, ""),
    ).toBe(false);
  });
});

// -------------------------------------------------------------- the sweep

describe("shouldDiscardDraft", () => {
  it("discards a draft nobody wrote anything into", () => {
    const { article: saved, fields } = loaded();

    expect(shouldDiscardDraft({ article: saved, fields, body: "" })).toBe(true);
  });

  it("keeps a draft whose headline was typed but not saved", () => {
    const { article: saved, fields } = loaded();

    expect(
      shouldDiscardDraft({
        article: saved,
        fields: { ...fields, title: "A headline" },
        body: "",
      }),
    ).toBe(false);
  });

  it("keeps a draft whose body was typed but not saved", () => {
    const { article: saved, fields } = loaded();

    expect(
      shouldDiscardDraft({ article: saved, fields, body: "Some prose." }),
    ).toBe(false);
  });

  it("discards a draft holding nothing but whitespace", () => {
    const { article: saved, fields } = loaded();

    expect(
      shouldDiscardDraft({
        article: saved,
        fields: { ...fields, title: "   " },
        body: "  \n ",
      }),
    ).toBe(true);
  });

  it("keeps a draft with a listing image the author just chose", () => {
    const { article: saved, fields } = loaded();

    expect(
      shouldDiscardDraft({
        article: saved,
        fields: { ...fields, listing_image_id: "image-1" },
        body: "",
      }),
    ).toBe(false);
  });

  it("keeps a draft the server already holds images for", () => {
    const { article: saved, fields } = loaded({ images: [image()] });

    expect(shouldDiscardDraft({ article: saved, fields, body: "" })).toBe(
      false,
    );
  });

  it("falls back to the article when the form has not loaded yet", () => {
    const saved = article({ title: "Saved headline" });

    expect(shouldDiscardDraft({ article: saved, fields: null, body: "" })).toBe(
      false,
    );
  });
});
