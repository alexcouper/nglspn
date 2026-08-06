import { test, expect, type Page } from "@playwright/test";
import * as path from "path";

const FIXTURES = path.join(__dirname, "fixtures");
const INLINE_IMAGE = path.join(FIXTURES, "inline-image.png");
const NOT_AN_IMAGE = path.join(FIXTURES, "not-an-image.txt");

async function login(page: Page) {
  const password = process.env.TEST_USER_PASSWORD;
  if (!password) {
    throw new Error(
      "TEST_USER_PASSWORD not set. Make sure .env.claude exists with credentials.",
    );
  }

  await page.goto("/login");
  await page.fill("#email", process.env.TEST_USER_EMAIL || "test@example.com");
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/my-projects/);
}

// Walks from the project list to a blank article editor, so the test doesn't
// hard-code a project slug. /new creates the draft immediately — an upload
// cannot name an article that does not exist yet — and swaps the URL, so this
// returns both ids.
async function openBlankArticleEditor(
  page: Page,
): Promise<{ projectId: string; articleId: string }> {
  await page.goto("/my-projects");
  await page.locator('a[href^="/my-projects/"]').last().click();
  await expect(page).toHaveURL(/\/my-projects\/[0-9a-f-]+$/);
  const projectId = page.url().split("/").pop()!;

  // The link lives behind a tab, so read the route off it rather than clicking.
  const newArticleHref = await page
    .locator('a[href$="/articles/new"]')
    .first()
    .getAttribute("href");
  await page.goto(newArticleHref!);
  await expect(page).toHaveURL(/\/articles\/edit\/[0-9a-f-]+$/);
  await expect(editorBody(page)).toBeVisible();

  return { projectId, articleId: page.url().split("/").pop()! };
}

// Article uploads are excluded from `project.images`, so cleanup cannot find
// them by listing the project. Record the ids the backend hands out instead.
function trackUploadedImageIds(page: Page): string[] {
  const ids: string[] = [];
  page.on("response", async (response) => {
    if (!response.url().endsWith("/images/upload-url") || !response.ok()) return;
    const body = await response.json().catch(() => null);
    if (body?.image_id) ids.push(body.image_id);
  });
  return ids;
}

// Deleting the draft cascades its linked images, but the ids are tracked and
// deleted too so a failure part-way through still cleans up. Every test now
// leaves a draft behind, because opening the editor creates one.
async function cleanUp(
  page: Page,
  projectId: string,
  articleId: string,
  imageIds: string[],
) {
  await page.evaluate(
    async ({ projectId, articleId, imageIds }) => {
      const apiUrl = "http://localhost:8000";
      const headers = {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      };

      await Promise.all(
        imageIds.map((imageId: string) =>
          fetch(
            `${apiUrl}/api/projects/${projectId}/articles/${articleId}/images/${imageId}`,
            { method: "DELETE", headers },
          ),
        ),
      );
      await fetch(`${apiUrl}/api/projects/${projectId}/articles/${articleId}`, {
        method: "DELETE",
        headers,
      });
    },
    { projectId, articleId, imageIds: imageIds.splice(0) },
  );
}

// The images linked to an article — the listing-image wizard's selection list.
async function articleImageIds(
  page: Page,
  projectId: string,
  articleId: string,
): Promise<string[]> {
  return page.evaluate(
    async ({ projectId, articleId }) => {
      const article = await fetch(
        `http://localhost:8000/api/projects/${projectId}/articles/${articleId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      ).then((r) => r.json());
      return (article.images ?? []).map((image: { id: string }) => image.id);
    },
    { projectId, articleId },
  );
}

// The gallery an author manages on the owner-facing project page.
async function galleryImageIds(
  page: Page,
  projectId: string,
): Promise<string[]> {
  return page.evaluate(async (projectId) => {
    const project = await fetch(
      `http://localhost:8000/api/my/projects/${projectId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      },
    ).then((r) => r.json());
    return (project.images ?? []).map((image: { id: string }) => image.id);
  }, projectId);
}

function editorBody(page: Page) {
  return page.locator('[contenteditable="true"]').first();
}

function insertedImage(page: Page) {
  return editorBody(page).locator("img").first();
}

// The toolbar's insert button drives a hidden file input rather than a dialog.
function imagePicker(page: Page) {
  return page.locator('.mdxeditor input[type="file"]').first();
}

// Next renders its own empty role="alert" route announcer, so pick ours out by
// its prefix.
function uploadAlert(page: Page) {
  return page.getByRole("alert").filter({ hasText: "Image upload failed" });
}

// Login is rate limited to 5/minute per IP, so the whole file shares one
// session rather than logging in per test.
test.describe.configure({ mode: "serial" });

test.describe("Article inline images", () => {
  let page: Page;
  let uploadedImageIds: string[];

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    uploadedImageIds = trackUploadedImageIds(page);
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
