import { test, expect, type Page } from "@playwright/test";

// The part of the article leave guard that jsdom cannot answer: whether a
// window-capture listener that only cancels the default really stops an App
// Router `Link`, with React's own event plumbing in the way.
//
// These tests do not drive the article editor. It needs a login, so the guard's
// click interceptor is transcribed here onto a public page and exercised there;
// what the editor does with the verdict is covered by
// `src/app/projects/[slug]/articles/use-leave-guard.test.tsx`.
//
// Needs a running Next dev server (`make dev` in src/web-ui). Not in CI, like
// the rest of `e2e/`.
//
// `SPIKE_APP_URL`, not `TEST_APP_URL`: `playwright.config.ts` parses
// `.env.claude` after the environment and overwrites `TEST_APP_URL` with
// whatever that file says, so it cannot be overridden from the command line.
// The port matters — `make dev` takes the first free port from 3000, so a
// second checkout running its own server is not on 3000.
const BASE = process.env.SPIKE_APP_URL ?? "http://localhost:3000";

// The feed streams in behind a Suspense boundary, so waiting for a row waits
// well past the point where the nav alone has rendered.
const feedRow = (page: Page) =>
  page.locator("main a[href^='/projects/']").first();

const siteLink = (page: Page) => page.locator("a[href='/projects']").first();

async function openHydrated(page: Page) {
  await page.goto(`${BASE}/latest`);
  await expect(feedRow(page)).toBeAttached({ timeout: 20_000 });
  await page.waitForTimeout(800);
}

// ------------------------------------------------- the click interceptor

// The guard's click interceptor, transcribed: a capture listener registered
// long after hydration that cancels the default and nothing else.
async function refuseLinkClicks(page: Page, on: "window" | "document") {
  await page.evaluate((target) => {
    const host = target === "window" ? window : document;
    const flags = window as unknown as { __saw: boolean; __bubbled: boolean };
    flags.__saw = false;
    flags.__bubbled = false;
    // Records that the click carried on past the interceptor, which is what
    // lets a menu link still run its own `closeMenu`.
    document.addEventListener("click", () => {
      flags.__bubbled = true;
    });
    host.addEventListener(
      "click",
      (event) => {
        if (!(event.target as Element | null)?.closest?.("a[href]")) return;
        flags.__saw = true;
        event.preventDefault();
      },
      true,
    );
  }, on);
}

async function clickSiteLink(page: Page) {
  await siteLink(page).click();
  await page.waitForTimeout(1200);
  return {
    url: page.url(),
    ...(await page.evaluate(() => {
      const flags = window as unknown as { __saw: boolean; __bubbled: boolean };
      return { saw: flags.__saw, bubbled: flags.__bubbled };
    })),
  };
}

test("preventDefault alone cancels an App Router Link", async ({ page }) => {
  await openHydrated(page);
  await refuseLinkClicks(page, "window");

  const result = await clickSiteLink(page);

  expect(result.saw).toBe(true);
  expect(result.url).toContain("/latest");
  // No `stopPropagation`: `Link` bails on `defaultPrevented`, and the click
  // still reaches the handlers that close the drawer and the user menu.
  expect(result.bubbled).toBe(true);
});

// Measured, not assumed. `app-index.js` hydrates the root into `document`, so
// it would be reasonable to expect a document-capture listener to lose to
// React's delegated one — it does not, in Next 16.1.6. The guard still uses
// `window`, because that is the one position in the capture path that no other
// listener and no React version can get in front of.
test("a document-capture listener happens to cancel it too", async ({
  page,
}) => {
  await openHydrated(page);
  await refuseLinkClicks(page, "document");

  const result = await clickSiteLink(page);

  expect(result.saw).toBe(true);
  expect(result.url).toContain("/latest");
});
