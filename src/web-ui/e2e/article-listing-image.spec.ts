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
      /\/api\/projects\/.*\/articles/.test(r.url()) &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  await saved;
}

// Switching to the listing tab saves first, so this waits on the same write.
async function openListingSettings(page: Page) {
  const saved = page.waitForResponse(
    (r) =>
      /\/api\/projects\/.*\/articles/.test(r.url()) &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("tab", { name: "Listing settings" }).click();
  await saved;
  await expect(page.getByLabel("Summary")).toBeVisible();
}

const listingThumb = (page: Page) => page.getByTestId("listing-image-thumb");

// Two uploads of the same fixture get different storage keys and identical
// filenames, so which one is showing is only answerable from the API.
async function savedListingImageId(
  page: Page,
  projectId: string,
  articleId: string,
): Promise<string | null> {
  const article = await fetchArticle(page, projectId, articleId);
  return (article.listing_image_id as string | null) ?? null;
}

// Scoped to the dialog: Next.js dev tools puts its own "Next" button on the
// page, and the editor has its own Remove/Change controls.
const wizard = (page: Page) => page.locator("dialog[open]");

// Picks the nth image in the wizard and frames it with the default rectangle.
async function chooseListingImage(page: Page, index: number) {
  await page.getByRole("button", { name: /Change|Choose an image/ }).click();
  await expect(
    wizard(page).getByRole("heading", { name: "Choose a listing image" }),
  ).toBeVisible();
  await wizard(page).locator("button[aria-pressed]").nth(index).click();
  await wizard(page).getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    wizard(page).getByRole("heading", { name: "Frame the card" }),
  ).toBeVisible();
  await wizard(page).getByRole("button", { name: "Use it" }).click();
  await expect(
    page.getByRole("heading", { name: "Frame the card" }),
  ).toHaveCount(0);
}

async function removeListingImage(page: Page) {
  await page.getByRole("button", { name: "Remove", exact: true }).click();
}

test.describe("Article listing image", () => {
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

  test("adopts the first body image, then keeps the author's choice", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await page.fill('input[placeholder="Article title"]', "Listing image test");
    await insertBodyImage(page, 0);
    await insertBodyImage(page, 1);
    await saveDraft(page);

    // auto mode: the earlier of the two uploads, resolved server-side on save.
    await openListingSettings(page);
    await expect(page.getByText("Following the first image")).toBeVisible();
    const [first, second] = uploadedImageIds;
    await expect(listingThumb(page)).toBeVisible();
    expect(await savedListingImageId(page, projectId, articleId)).toBe(first);

    // Choosing the second one commits it, and it survives a save and a reload.
    await chooseListingImage(page, 1);
    await expect(page.getByText("Your choice.")).toBeVisible();
    await saveDraft(page);

    await page.reload();
    await openListingSettings(page);
    await expect(page.getByText("Your choice.")).toBeVisible();
    expect(await savedListingImageId(page, projectId, articleId)).toBe(second);

    // Removal sticks: it is a mode, not an empty id the next save re-fills.
    await removeListingImage(page);
    await expect(page.getByText("shows no image in listings")).toBeVisible();
    await saveDraft(page);

    await page.reload();
    await openListingSettings(page);
    await expect(page.getByText("shows no image in listings")).toBeVisible();
    await expect(listingThumb(page)).toHaveCount(0);
    expect(await savedListingImageId(page, projectId, articleId)).toBeNull();

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("previews an imageless article as a text-only card in both variants", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await page.fill('input[placeholder="Article title"]', "No image at all");
    await editorBody(page).fill("A body with no pictures in it whatsoever.");

    await openListingSettings(page);

    // No image was ever uploaded, so `auto` resolves to nothing.
    await expect(listingThumb(page)).toHaveCount(0);
    for (const variant of ["As lead story", "In the grid"]) {
      await page.getByRole("tab", { name: variant }).click();
      const card = page.locator("article").first();
      await expect(card).toBeVisible();
      await expect(card.locator("img")).toHaveCount(0);
      await expect(card).toContainText("No image at all");
    }

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });
});
