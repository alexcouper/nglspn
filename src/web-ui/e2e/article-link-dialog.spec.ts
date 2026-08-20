import { test, expect, type Page } from "@playwright/test";
import {
  allowLeavingTheEditor,
  cleanUp,
  editorBody,
  login,
  openBlankArticleEditor,
} from "./helpers";

const LINK_BUTTON = 'button[aria-label="Create link"]';
const LINK_DIALOG = '[class*="linkDialogPopoverContent"]';

// One login for the file: /api/auth/login allows 5/min per IP.
test.describe.configure({ mode: "serial" });

async function typeParagraphs(page: Page, count: number) {
  await editorBody(page).click();
  for (let index = 0; index < count; index++) {
    await page.keyboard.type(
      `Paragraph number ${index} with some words in it.`,
    );
    await page.keyboard.press("Enter");
  }
}

// What a click at the button's centre would land on. `toBeVisible` does not
// catch this: an element covered by the site header is still visible to
// Playwright.
async function centreOfLinkButtonHitsIt(page: Page): Promise<boolean> {
  return page.evaluate((selector) => {
    const button = document.querySelector(selector);
    if (!button) return false;
    const box = button.getBoundingClientRect();
    const hit = document.elementFromPoint(
      box.left + box.width / 2,
      box.top + box.height / 2,
    );
    return !!hit && button.contains(hit);
  }, LINK_BUTTON);
}

async function isWithinViewport(
  page: Page,
  selector: string,
): Promise<boolean> {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    const box = el.getBoundingClientRect();
    return box.top >= 0 && box.bottom <= window.innerHeight;
  }, selector);
}

test.describe("Article link dialog", () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    allowLeavingTheEditor(page);
    await login(page);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test("link button stays clickable after scrolling into a long article", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);

    try {
      // Long enough that the toolbar has scrolled up into the sticky chrome.
      await typeParagraphs(page, 40);

      const target = editorBody(page).locator("p", {
        hasText: "Paragraph number 35",
      });
      await target.scrollIntoViewIfNeeded();
      await target.dblclick();

      expect(await centreOfLinkButtonHitsIt(page)).toBe(true);

      await page.locator(LINK_BUTTON).click();

      await expect(page.locator(LINK_DIALOG)).toBeVisible();
      expect(await isWithinViewport(page, LINK_DIALOG)).toBe(true);
    } finally {
      await cleanUp(page, projectId, articleId);
    }
  });

  test("link button opens the dialog in a short article", async () => {
    const { projectId, articleId } = await openBlankArticleEditor(page);

    try {
      await editorBody(page).click();
      await page.keyboard.type("Just a short sentence here.");
      await editorBody(page).locator("p").first().dblclick();

      expect(await centreOfLinkButtonHitsIt(page)).toBe(true);
      await page.locator(LINK_BUTTON).click();

      await expect(page.locator(LINK_DIALOG)).toBeVisible();
      expect(await isWithinViewport(page, LINK_DIALOG)).toBe(true);
    } finally {
      await cleanUp(page, projectId, articleId);
    }
  });
});
