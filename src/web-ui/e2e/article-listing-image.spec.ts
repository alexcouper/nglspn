import { test, expect, type Page } from "@playwright/test";
import * as path from "path";
import {
  allowLeavingTheEditor,
  cleanUp,
  editorBody,
  fetchArticle,
  imagePicker,
  login,
  openBlankArticleEditor,
  trackUploadedImageIds,
} from "./helpers";

const FIXTURES = path.join(__dirname, "fixtures");
const IMAGE = path.join(FIXTURES, "inline-image.png");

// One login for the file: /api/auth/login allows 5/min per IP. Projects also
// cap at 10 gallery images — article uploads do not count towards that, but
// each test still puts its own uploads back.
test.describe.configure({ mode: "serial" });

const bodyImages = (page: Page) => editorBody(page).locator("img");

async function insertBodyImage(page: Page, index: number) {
  await imagePicker(page).setInputFiles(IMAGE);
  await expect(bodyImages(page)).toHaveCount(index + 1, { timeout: 30_000 });
}

// Waits for the write itself rather than the "Draft saved" message, which
// clears after 2.5s and would race the next save.
async function saveDraft(page: Page) {
  const saved = page.waitForResponse(
    (r) =>
      /\/api\/articles\//.test(r.url()) &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  await saved;
}

// Switching to the preview saves first, so this waits on the same write.
async function openPreview(page: Page) {
  const saved = page.waitForResponse(
    (r) =>
      /\/api\/articles\//.test(r.url()) &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Preview" }).click();
  await saved;
  await expect(page.getByRole("tab", { name: "The article" })).toBeVisible();
}

async function backToEditing(page: Page) {
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByTestId("cover-slot")).toBeVisible();
}

const coverSlot = (page: Page) => page.getByTestId("cover-slot");
const coverImage = (page: Page) => coverSlot(page).locator("img");

// Two uploads of the same fixture get different storage keys and identical
// filenames, so which one is showing is only answerable from the API.
async function savedListingImageId(
  page: Page,
  projectId: string,
  articleId: string,
): Promise<string | null> {
  const article = await fetchArticle(page, articleId);
  return (article.listing_image_id as string | null) ?? null;
}

// Scoped to the dialog: Next.js dev tools puts its own "Next" button on the
// page, and the editor has its own Remove/Change controls.
const wizard = (page: Page) => page.locator("dialog[open]");

// Picks the nth image in the dialog and frames it with the default rectangle.
async function chooseCover(page: Page, index: number) {
  await page.getByRole("button", { name: /Change|Add a cover image/ }).click();
  await expect(
    wizard(page).getByRole("heading", { name: "Choose a cover image" }),
  ).toBeVisible();
  await wizard(page).locator("button[aria-pressed]").nth(index).click();
  await wizard(page).getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    wizard(page).getByRole("heading", { name: "Frame the cover" }),
  ).toBeVisible();
  await wizard(page).getByRole("button", { name: "Use it" }).click();
  await expect(
    page.getByRole("heading", { name: "Frame the cover" }),
  ).toHaveCount(0);
}

async function removeCover(page: Page) {
  await page.getByRole("button", { name: "Remove cover" }).click();
}

test.describe("Article cover", () => {
  let page: Page;
  let uploadedImageIds: string[];

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    uploadedImageIds = trackUploadedImageIds(page);
    allowLeavingTheEditor(page);
    await login(page);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test("a body image is not the cover until the author picks it", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await page.fill('input[placeholder="Article title"]', "Cover test");
    await insertBodyImage(page, 0);
    await insertBodyImage(page, 1);
    await saveDraft(page);

    // Nothing is derived from the body: the slot is empty and so is the card.
    await expect(coverImage(page)).toHaveCount(0);
    expect(await savedListingImageId(page, projectId, articleId)).toBeNull();

    // Choosing the second upload makes it the cover and the card image, and
    // it survives a save and a reload.
    const [, second] = uploadedImageIds;
    await chooseCover(page, 1);
    await expect(coverImage(page)).toBeVisible();
    await saveDraft(page);

    await page.reload();
    await expect(coverImage(page)).toBeVisible();
    expect(await savedListingImageId(page, projectId, articleId)).toBe(second);

    await openPreview(page);
    await page.getByRole("tab", { name: "As lead story" }).click();
    await expect(page.locator("article img").first()).toBeVisible();
    await backToEditing(page);

    // Removal sticks across a save.
    await removeCover(page);
    await expect(coverImage(page)).toHaveCount(0);
    await saveDraft(page);

    await page.reload();
    await expect(coverImage(page)).toHaveCount(0);
    expect(await savedListingImageId(page, projectId, articleId)).toBeNull();

    await cleanUp(page, articleId, uploadedImageIds);
  });

  test("previews an article without a cover as a text-only card", async () => {
    const { articleId } = await openBlankArticleEditor(page);
    await page.fill('input[placeholder="Article title"]', "No image at all");
    await editorBody(page).fill("A body with no pictures in it whatsoever.");

    await openPreview(page);

    await expect(page.locator("h1", { hasText: "No image at all" })).toBeVisible();
    for (const variant of ["As lead story", "In the grid"]) {
      await page.getByRole("tab", { name: variant }).click();
      const card = page.locator("article").first();
      await expect(card).toBeVisible();
      await expect(card.locator("img")).toHaveCount(0);
      await expect(card).toContainText("No image at all");
    }

    await cleanUp(page, articleId, uploadedImageIds);
  });
});
