import { test, expect, type Page } from "@playwright/test";
import * as path from "path";

const FIXTURES = path.join(__dirname, "fixtures");
const HERO_IMAGE = path.join(FIXTURES, "inline-image.png");
const HERO_IMAGE_NAME = "inline-image.png";

// /api/auth/login is rate limited to 5/min per IP, so this file logs in once
// and runs serially.
test.describe.configure({ mode: "serial" });

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
  await expect(page.locator('input[placeholder="Article title"]')).toBeVisible();

  return projectId;
}

// The clear control is icon-only with title="Remove hero image"
// (HeroImageUploader.tsx:45).
const removeHero = (page: Page) => page.getByTitle("Remove hero image");

// HeroImageUploader renders above ArticleEditor, and the editor's own hidden
// picker lives inside `.mdxeditor`, so the hero's input is the first on the
// page. If that ever stopped holding, the hero-preview assertion below fails
// rather than the test quietly exercising the wrong control.
const heroFileInput = (page: Page) =>
  page.locator('input[type="file"]').first();

// Waits for the write itself rather than the "Draft saved" message, which
// clears after 2.5s and would race the second save.
async function saveDraft(page: Page) {
  const saved = page.waitForResponse(
    (r) =>
      /\/api\/projects\/.*\/articles/.test(r.url()) &&
      r.request().method() !== "GET",
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  await saved;
}

// Projects cap out at 10 images, so a test that uploads has to put its own
// uploads back or the suite stops working after a few runs. Removes the draft
// this spec created and any image matching its fixture filename.
async function cleanUp(page: Page, projectId: string, articleId: string) {
  await page.evaluate(
    async ({ projectId, articleId, filename }) => {
      const apiUrl = "http://localhost:8000";
      const headers = {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      };

      const project = await fetch(`${apiUrl}/api/my/projects/${projectId}`, {
        headers,
      }).then((r) => r.json());

      await fetch(
        `${apiUrl}/api/projects/${projectId}/articles/${articleId}`,
        { method: "DELETE", headers },
      );

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
    { projectId, articleId, filename: HERO_IMAGE_NAME },
  );
}

test("removing a hero image and saving actually removes it", async ({
  page,
}) => {
  await login(page);
  const projectId = await openBlankArticleEditor(page);

  await page.fill('input[placeholder="Article title"]', "Hero removal test");
  await heroFileInput(page).setInputFiles(HERO_IMAGE);
  await expect(removeHero(page)).toBeVisible();

  await saveDraft(page);
  await expect(page).toHaveURL(/\/articles\/edit\/[0-9a-f-]+$/);
  const editUrl = page.url();
  const articleId = editUrl.split("/").pop()!;

  await removeHero(page).click();
  await expect(removeHero(page)).toHaveCount(0);
  await saveDraft(page);

  // The regression: before the fix, the hero came back on reload.
  await page.goto(editUrl);
  await expect(page.getByRole("button", { name: "Save draft" })).toBeVisible();
  await expect(removeHero(page)).toHaveCount(0);

  await cleanUp(page, projectId, articleId);
});
