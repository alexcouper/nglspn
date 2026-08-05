import { test, expect, type Page } from "@playwright/test";
import * as path from "path";

const FIXTURES = path.join(__dirname, "fixtures");
const INLINE_IMAGE = path.join(FIXTURES, "inline-image.png");
const INLINE_IMAGE_NAME = "inline-image.png";
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
// hard-code a project slug. Returns the project id, for cleanup.
async function openBlankArticleEditor(page: Page): Promise<string> {
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
  await expect(editorBody(page)).toBeVisible();

  return projectId;
}

// Projects cap out at 10 images, so a test that uploads has to put its own
// uploads back or the suite stops working after a few runs. Only images this
// spec created (matched on filename) are removed.
async function deleteUploadedFixtures(page: Page, projectId: string) {
  await page.evaluate(
    async ({ projectId, filename }) => {
      const apiUrl = "http://localhost:8000";
      const headers = {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      };

      const project = await fetch(`${apiUrl}/api/my/projects/${projectId}`, {
        headers,
      }).then((r) => r.json());

      const ours = (project.images ?? []).filter(
        (image: { original_filename: string }) =>
          image.original_filename === filename,
      );

      await Promise.all(
        ours.map((image: { id: string }) =>
          fetch(`${apiUrl}/api/my/projects/${projectId}/images/${image.id}`, {
            method: "DELETE",
            headers,
          }),
        ),
      );
    },
    { projectId, filename: INLINE_IMAGE_NAME },
  );
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

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await login(page);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test("inserts an image straight from the file picker", async () => {
    const projectId = await openBlankArticleEditor(page);

    await imagePicker(page).setInputFiles(INLINE_IMAGE);

    await expect(insertedImage(page)).toBeVisible({ timeout: 30_000 });
    await expect(insertedImage(page)).toHaveAttribute("alt", "");

    await deleteUploadedFixtures(page, projectId);
  });

  test("edits alt text without losing the image", async () => {
    const projectId = await openBlankArticleEditor(page);
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

    await deleteUploadedFixtures(page, projectId);
  });

  test("shows a rejected upload instead of failing silently", async () => {
    await openBlankArticleEditor(page);

    // Rejected client-side by uploadProjectImage, so nothing reaches storage.
    await imagePicker(page).setInputFiles(NOT_AN_IMAGE);

    await expect(uploadAlert(page)).toBeVisible();
    await expect(uploadAlert(page)).toContainText("Invalid file type");
  });
});
