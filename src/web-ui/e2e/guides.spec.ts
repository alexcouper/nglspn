import { expect, test } from "@playwright/test";

// These reading pages only need the frontend, not a backend or test account.
for (const language of ["en", "is"] as const) {
  const prefix = language === "is" ? "/is/guides" : "/guides";

  test(`${language}: every guide hydrates without browser errors`, async ({ page }) => {
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    await page.goto(prefix);
    // Wait for the shared auth navigation to hydrate, not just the static
    // article. This catches a race when it is given its own Suspense boundary.
    const loginLink = page.locator("nav.fixed a").filter({ hasText: /^Log in$/ });
    await expect(loginLink).toHaveCount(1);
    const paths = await page.locator(`main a[href^="${prefix}/"]`).evaluateAll(
      (links) => [...new Set(links.map((link) => link.getAttribute("href")!))],
    );
    expect(paths).toHaveLength(9);
    for (const path of paths) {
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(loginLink).toHaveCount(1);
    }
    expect(browserErrors).toEqual([]);
  });

  test(`${language}: guides stay visible with JavaScript disabled`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
    const page = await context.newPage();
    for (const path of [prefix, `${prefix}/contribute-to-projects`, `${prefix}/contribute-to-projects/first-contribution`]) {
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.locator("main")).toHaveAttribute("lang", language);
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", `https://naglasupan.is${path}`);
      await expect(page.locator('link[rel="alternate"][hreflang]')).toHaveCount(3);
      if (path !== prefix) {
        await expect(page.locator("article section").first()).toBeVisible();
        await expect(page.locator('main script[type="application/ld+json"]')).toHaveCount(1);
      }
    }
    await context.close();
  });

  test(`${language}: mobile language switch keeps the current guide`, async ({ page }) => {
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    await page.setViewportSize({ width: 390, height: 844 });
    const slug = "/share-a-side-project/project-page-checklist";
    await page.goto(`${prefix}${slug}`);
    await expect(page.locator("main h1")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    const otherLanguage = language === "is" ? "en" : "is";
    const otherPrefix = language === "is" ? "/guides" : "/is/guides";
    await page.locator(`main a[hreflang="${otherLanguage}"]`).click();
    await expect(page).toHaveURL(new RegExp(`${otherPrefix}${slug}$`));
    await expect(page.locator("main")).toHaveAttribute("lang", otherLanguage);
    await expect(page.locator("main h1")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(browserErrors).toEqual([]);
  });

  test(`${language}: unknown guides return 404`, async ({ request }) => {
    expect((await request.get(`${prefix}/not-a-guide`)).status()).toBe(404);
  });
}
