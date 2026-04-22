import { test, expect } from "@playwright/test";

// Preconditions for this suite:
//   - Django backend reachable at $API_URL (default http://localhost:8001) with
//     migration 0003_seed_phase2_ui_chrome applied (which seeds the
//     Icelandic labels used by Navigation and Footer).
//   - Web-ui dev server running at Playwright's baseURL (default http://localhost:3000).

test("renders Icelandic nav at /is", async ({ page }) => {
  await page.goto("/is");
  await expect(page.getByRole("link", { name: "Verkefni" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Keppnir" }).first()).toBeVisible();
});

test("renders English nav at /en", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("link", { name: "Projects" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Competitions" }).first()).toBeVisible();
});

test("locale switcher toggles between is and en", async ({ page }) => {
  // Start at English and verify English content
  await page.goto("/en");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("link", { name: "Projects" }).first()).toBeVisible();

  // Click the locale switcher button to switch to Icelandic
  const icelandicButton = page.locator("nav").getByRole("button", { name: /Switch to Íslenska/ });
  await expect(icelandicButton).toBeVisible();

  // Wait for reload after click
  await Promise.all([
    page.waitForLoadState("networkidle"),
    icelandicButton.click(),
  ]);

  // After switching, verify Icelandic content appears
  await expect(page.getByRole("link", { name: "Verkefni" }).first()).toBeVisible();

  // Click the locale switcher button to switch back to English
  const englishButton = page.locator("nav").getByRole("button", { name: /Switch to English/ });
  await expect(englishButton).toBeVisible();

  // Wait for reload after click
  await Promise.all([
    page.waitForLoadState("networkidle"),
    englishButton.click(),
  ]);

  // After switching back, verify English content reappears
  await expect(page.getByRole("link", { name: "Projects" }).first()).toBeVisible();
});
