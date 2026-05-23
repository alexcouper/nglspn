import { test, expect } from "@playwright/test";

const COMPETITION_PATH =
  process.env.TEST_VOTING_COMPETITION_PATH ?? "/competitions/mars-keppni-2025";

test.describe("Competition voting page (assigned reviewer)", () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;
    if (!email || !password) {
      throw new Error(
        "TEST_USER_EMAIL / TEST_USER_PASSWORD must be set (source .env.claude)"
      );
    }
    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/my-projects/);
  });

  test("renders ranked cards in place of the All Projects grid", async ({ page }) => {
    await page.goto(COMPETITION_PATH);

    await expect(page.getByRole("heading", { name: "My Ranking" })).toBeVisible();

    // The "All Projects" header is suppressed while ranking is rendered
    await expect(
      page.getByRole("heading", { name: "All Projects" })
    ).toHaveCount(0);

    // At least one ranked card exists and rank-badge "1" is on the first
    const cards = page.getByTestId("ranked-card");
    await expect(cards.first()).toBeVisible();
    await expect(cards.first().getByTestId("rank-badge")).toHaveText("1");

    await expect(page.getByRole("button", { name: "Submit Ranking" })).toBeEnabled();
  });

  test("reorder via chevron updates the saved indicator", async ({ page }) => {
    await page.goto(COMPETITION_PATH);

    const firstCard = page.getByTestId("ranked-card").first();
    await firstCard.getByRole("button", { name: /Move .* down/ }).click();

    // 500ms debounce + network round-trip; allow generous headroom for CI
    await expect(page.getByText("Saving…")).toBeVisible({ timeout: 5_000 });
  });
});
