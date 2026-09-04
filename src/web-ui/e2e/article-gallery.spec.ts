import { test, expect, type Page } from "@playwright/test";
import * as fs from "fs";
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

const INLINE_IMAGE = path.join(__dirname, "fixtures", "inline-image.png");

// One login for the file: /api/auth/login allows 5/min per IP.
test.describe.configure({ mode: "serial" });

const bodyImages = (page: Page) => editorBody(page).locator("img");
const gallery = (page: Page) => editorBody(page).locator(".article-gallery");
const gallerySlides = (page: Page) =>
  gallery(page).getByRole("button", { name: /^Show image \d+$/ });

async function insertImage(page: Page, index: number) {
  await imagePicker(page).setInputFiles(INLINE_IMAGE);
  await expect(bodyImages(page)).toHaveCount(index + 1, { timeout: 30_000 });
}

async function saveDraft(page: Page) {
  const saved = page.waitForResponse(
    (r) =>
      /\/api\/projects\/.*\/articles/.test(r.url()) &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  await saved;
}

/**
 * Drops an image file onto `selector`.
 *
 * Playwright cannot drive an OS drag, so the DataTransfer is built in the page
 * and the two events the drop handler needs are dispatched by hand. What the
 * handler reads — `items` for the file, `types` for the payload kind — is the
 * same either way.
 */
async function dropImageFileOn(page: Page, selector: string) {
  const base64 = fs.readFileSync(INLINE_IMAGE).toString("base64");

  await page.evaluate(
    async ({ selector, base64 }) => {
      const target = document.querySelector(selector);
      if (!target) throw new Error(`nothing to drop on: ${selector}`);

      const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
      const file = new File([bytes], "dropped.png", { type: "image/png" });
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);

      for (const type of ["dragover", "drop"]) {
        target.dispatchEvent(
          new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer }),
        );
      }
    },
    { selector, base64 },
  );
}

test.describe("Article image galleries", () => {
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

  test("dropping an image onto an image turns the pair into a gallery", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await insertImage(page, 0);

    await dropImageFileOn(page, ".markdown-article img");

    await expect(gallery(page)).toBeVisible({ timeout: 30_000 });
    await expect(gallerySlides(page)).toHaveCount(2);
    // A carousel shows one at a time — the second image is in the block, not
    // on the page.
    await expect(bodyImages(page)).toHaveCount(1);

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("dropping onto the gallery adds another image to it", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await insertImage(page, 0);
    await dropImageFileOn(page, ".markdown-article img");
    await expect(gallerySlides(page)).toHaveCount(2, { timeout: 30_000 });

    await dropImageFileOn(page, ".article-gallery img");

    await expect(gallerySlides(page)).toHaveCount(3, { timeout: 30_000 });

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("saves the gallery as a :::gallery block", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await insertImage(page, 0);
    await dropImageFileOn(page, ".markdown-article img");
    await expect(gallerySlides(page)).toHaveCount(2, { timeout: 30_000 });

    await saveDraft(page);

    // The exact shape `article-gallery.test.tsx` renders through the read
    // pipeline: a container directive, one image per line, blank line between.
    const article = await fetchArticle(page, projectId, articleId);
    expect(article.body).toMatch(
      /:::gallery\n!\[\]\(\S+\)\n\n!\[\]\(\S+\)\n:::/,
    );

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("reorders and removes images from the gallery", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await insertImage(page, 0);
    await dropImageFileOn(page, ".markdown-article img");
    await expect(gallerySlides(page)).toHaveCount(2, { timeout: 30_000 });
    await dropImageFileOn(page, ".article-gallery img");
    await expect(gallerySlides(page)).toHaveCount(3, { timeout: 30_000 });

    await page.getByRole("button", { name: "Move image right" }).click();
    await expect(gallerySlides(page)).toHaveCount(3);

    await page
      .getByRole("button", { name: "Remove image from gallery" })
      .click();

    await expect(gallerySlides(page)).toHaveCount(2);

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });

  test("collapses back to a plain image when only one is left", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);
    await insertImage(page, 0);
    await dropImageFileOn(page, ".markdown-article img");
    await expect(gallerySlides(page)).toHaveCount(2, { timeout: 30_000 });

    await page
      .getByRole("button", { name: "Remove image from gallery" })
      .click();

    await expect(gallery(page)).toHaveCount(0);
    await expect(bodyImages(page)).toHaveCount(1);

    await saveDraft(page);
    const article = await fetchArticle(page, projectId, articleId);
    expect(article.body).not.toContain(":::gallery");

    await cleanUp(page, projectId, articleId, uploadedImageIds);
  });
});
