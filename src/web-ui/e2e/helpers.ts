import { expect, type Page } from "@playwright/test";

/*
 * Shared walk-ins for the article editor specs. Anything used by one spec only
 * stays in that spec.
 */

// The e2e stack is `make dev` in both services, so the backend origin is fixed.
// Passed into `page.evaluate` rather than closed over — that code runs in the
// browser, where this module does not exist.
export const API_URL = "http://localhost:8000";

// Credentials come from .env.claude, which playwright.config.ts parses itself.
// Login is rate limited to 5/min per IP, so a spec logs in once in `beforeAll`
// against a shared page and runs `mode: "serial"`, not once per test.
export async function login(page: Page) {
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

export const editorBody = (page: Page) =>
  page.locator('[contenteditable="true"]').first();

// The toolbar's insert button drives a hidden file input rather than a dialog.
export const imagePicker = (page: Page) =>
  page.locator('.mdxeditor input[type="file"]').first();

// Walks from the project list to a blank article editor, so specs don't
// hard-code a project slug. The New article button is what creates the draft —
// there is no editor route to navigate to instead — so this returns both ids.
// Settling on the editor means the title input is up too; it renders first.
export async function openBlankArticleEditor(
  page: Page,
): Promise<{ projectId: string; articleId: string }> {
  await page.goto("/my-projects");
  await page.locator('a[href^="/my-projects/"]').last().click();
  await expect(page).toHaveURL(/\/my-projects\/[0-9a-f-]+$/);
  const projectId = page.url().split("/").pop()!;

  await page.getByRole("button", { name: "Articles", exact: true }).click();
  await page.getByRole("button", { name: "New article" }).click();
  await expect(page).toHaveURL(/\/articles\/edit\/[0-9a-f-]+$/);
  await expect(editorBody(page)).toBeVisible();

  return { projectId, articleId: page.url().split("/").pop()! };
}

// Article uploads are excluded from `project.images`, so cleanup cannot find
// them by listing the project. Record the ids the backend hands out instead.
export function trackUploadedImageIds(page: Page): string[] {
  const ids: string[] = [];
  page.on("response", async (response) => {
    if (!response.url().endsWith("/images/upload-url") || !response.ok())
      return;
    const body = await response.json().catch(() => null);
    if (body?.image_id) ids.push(body.image_id);
  });
  return ids;
}

// The article's JSON, for assertions the DOM cannot answer — two uploads of one
// fixture look identical on screen but carry different ids.
export async function fetchArticle(
  page: Page,
  projectId: string,
  articleId: string,
): Promise<Record<string, unknown>> {
  return page.evaluate(
    async ({ apiUrl, projectId, articleId }) =>
      fetch(`${apiUrl}/api/projects/${projectId}/articles/${articleId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      }).then((r) => r.json()),
    { apiUrl: API_URL, projectId, articleId },
  );
}

// Deleting the article cascades its linked images; tracked ids are deleted too
// so a run that failed part-way still cleans up. Every test leaves a draft
// behind, because opening the editor creates one.
export async function cleanUp(
  page: Page,
  projectId: string,
  articleId: string,
  imageIds: string[] = [],
) {
  await page.evaluate(
    async ({ apiUrl, projectId, articleId, imageIds }) => {
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
    { apiUrl: API_URL, projectId, articleId, imageIds: imageIds.splice(0) },
  );
}

// The editor guards against losing an unsaved body, so navigating away from it
// raises a beforeunload prompt. Every navigation in these specs is deliberate.
export function allowLeavingTheEditor(page: Page) {
  page.on("dialog", (dialog) => {
    if (dialog.type() === "beforeunload") {
      void dialog.accept();
    } else {
      void dialog.dismiss();
    }
  });
}
