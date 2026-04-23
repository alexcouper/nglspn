import { test, expect } from "@playwright/test";

// Preconditions:
//   - Django backend reachable at $API_URL with phase 1+2+4 migrations applied
//     and the webhook env vars set (so PATCH triggers revalidation).
//   - Web-ui dev server running at Playwright's baseURL.
//   - $TEST_USER_EMAIL / $TEST_USER_PASSWORD valid in .env.claude.

const EMAIL = process.env.TEST_USER_EMAIL!;
const PASSWORD = process.env.TEST_USER_PASSWORD!;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(EMAIL);
  await page.getByLabel(/password/i).fill(PASSWORD);
  await page.getByRole("button", { name: /log in|sign in/i }).click();
  await page.waitForURL(/\/$|\/projects|\/onboarding/);
}

test("inline edit: edit nav.projects, see change instantly, persist after reload", async ({
  page,
}) => {
  test.skip(!EMAIL || !PASSWORD, "TEST_USER_EMAIL/PASSWORD not set");

  await login(page);
  await page.goto("/");

  // Open user menu and toggle edit mode on.
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  await page.getByRole("menuitem", { name: /edit translations/i }).click();

  // Re-open menu and verify "on" label.
  await page.locator("nav").getByRole("button", { name: /user menu/i }).click();
  await expect(
    page.getByRole("menuitem", { name: /editing translations: on/i }),
  ).toBeVisible();
  await page.keyboard.press("Escape");

  // Hover the Verkefni link → pencil appears → click it.
  const verkefni = page.getByRole("link", { name: "Verkefni" }).first();
  await verkefni.hover();
  const pencil = page
    .locator(`[data-i18n-key="nav.projects"] button[aria-label*="Edit translation"]`);
  await pencil.click();

  // Popover opens; edit and save.
  const popover = page.getByRole("dialog", { name: /edit translation/i });
  await expect(popover).toBeVisible();

  const editor = popover.getByRole("textbox");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.press("Delete");
  await page.keyboard.type("VERKVERK");

  await popover.getByRole("button", { name: /^save$/i }).click();

  // Optimistic update: nav re-renders without reload.
  await expect(
    page.getByRole("link", { name: "VERKVERK" }).first(),
  ).toBeVisible({ timeout: 3000 });

  // Reload — value should persist.
  await page.reload();
  await expect(
    page.getByRole("link", { name: "VERKVERK" }).first(),
  ).toBeVisible({ timeout: 5000 });

  // Best-effort cleanup: revert via UI.
  const verkverk = page.getByRole("link", { name: "VERKVERK" }).first();
  await verkverk.hover();
  const pencil2 = page
    .locator(`[data-i18n-key="nav.projects"] button[aria-label*="Edit translation"]`);
  if (await pencil2.isVisible()) {
    await pencil2.click();
    const popover2 = page.getByRole("dialog", { name: /edit translation/i });
    const editor2 = popover2.getByRole("textbox");
    await editor2.click();
    await page.keyboard.press("Control+A");
    await page.keyboard.press("Delete");
    await page.keyboard.type("Verkefni");
    await popover2.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByRole("link", { name: "Verkefni" }).first()).toBeVisible({
      timeout: 3000,
    });
  }
});
