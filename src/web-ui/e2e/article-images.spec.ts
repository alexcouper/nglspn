import { test, expect, type Page } from "@playwright/test";
import * as path from "path";
import {
  allowLeavingTheEditor,
  API_URL,
  cleanUp,
  editorBody,
  fetchArticle,
  imagePicker,
  login,
  openBlankArticleEditor,
  trackUploadedImageIds,
} from "./helpers";

const FIXTURES = path.join(__dirname, "fixtures");
const INLINE_IMAGE = path.join(FIXTURES, "inline-image.png");
const NOT_AN_IMAGE = path.join(FIXTURES, "not-an-image.txt");

// One login for the file: /api/auth/login allows 5/min per IP.
test.describe.configure({ mode: "serial" });

function insertedImage(page: Page) {
  return editorBody(page).locator("img").first();
}

// Next renders its own empty role="alert" route announcer, so pick ours out by
// its prefix.
function uploadAlert(page: Page) {
  return page.getByRole("alert").filter({ hasText: "Image upload failed" });
}

// The images linked to an article — the listing-image wizard's selection list.
async function articleImageIds(
  page: Page,
  projectId: string,
  articleId: string,
): Promise<string[]> {
  const article = await fetchArticle(page, projectId, articleId);
  const images = (article.images ?? []) as { id: string }[];
  return images.map((image) => image.id);
}

// The gallery an author manages on the owner-facing project page.
async function galleryImageIds(
  page: Page,
  projectId: string,
): Promise<string[]> {
  return page.evaluate(
    async ({ apiUrl, projectId }) => {
      const project = await fetch(`${apiUrl}/api/my/projects/${projectId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      }).then((r) => r.json());
      return (project.images ?? []).map((image: { id: string }) => image.id);
    },
    { apiUrl: API_URL, projectId },
  );
}

test.describe("Article inline images", () => {
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

  test("inserts an image straight from the file picker", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);

    await imagePicker(page).setInputFiles(INLINE_IMAGE);

    await expect(insertedImage(page)).toBeVisible({ timeout: 30_000 });
    await expect(insertedImage(page)).toHaveAttribute("alt", "");

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("links the inserted image to the article it was uploaded for", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);

    await imagePicker(page).setInputFiles(INLINE_IMAGE);
    await expect(insertedImage(page)).toBeVisible({ timeout: 30_000 });

    // The link is what makes the image offerable in the listing-image wizard,
    // and what keeps it out of the project gallery.
    const linked = await articleImageIds(page, projectId, articleId);
    expect(linked).toEqual([uploadedImageIds[0]]);

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("edits alt text without losing the image", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await imagePicker(page).setInputFiles(INLINE_IMAGE);
    await expect(insertedImage(page)).toBeVisible({ timeout: 30_000 });
    const srcBeforeEdit = await insertedImage(page).getAttribute("src");

    await insertedImage(page).click();
    await page.locator('button[title="Edit image"]').click();
    await page.fill("#image-alt", "A gradient test image");
    await page
      .locator("dialog[open]")
      .getByRole("button", { name: "Save", exact: true })
      .click();

    await expect(insertedImage(page)).toHaveAttribute(
      "alt",
      "A gradient test image",
    );
    // The save payload has to echo the original src back, or the plugin blanks it.
    await expect(insertedImage(page)).toHaveAttribute("src", srcBeforeEdit!);

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("keeps the inserted image out of the project's own gallery", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    const galleryBefore = await galleryImageIds(page, projectId);

    await imagePicker(page).setInputFiles(INLINE_IMAGE);
    await expect(insertedImage(page)).toBeVisible({ timeout: 30_000 });

    // Matched on id rather than filename: a pre-existing upload of the same
    // fixture can legitimately sit in the gallery.
    expect(uploadedImageIds).toHaveLength(1);
    const galleryAfter = await galleryImageIds(page, projectId);
    expect(galleryAfter).not.toContain(uploadedImageIds[0]);
    expect(galleryAfter).toEqual(galleryBefore);

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("shows a rejected upload instead of failing silently", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);

    // Rejected client-side by uploadProjectImage, so nothing reaches storage.
    await imagePicker(page).setInputFiles(NOT_AN_IMAGE);

    await expect(uploadAlert(page)).toBeVisible();
    await expect(uploadAlert(page)).toContainText("Invalid file type");

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });
});
