import { test, expect } from "@playwright/test";

test.describe("Login", () => {
  test("should login successfully with valid credentials", async ({ page }) => {
    const email = process.env.TEST_USER_EMAIL || "test@example.com";
    const password = process.env.TEST_USER_PASSWORD;

    if (!password) {
      throw new Error(
        "TEST_USER_PASSWORD not set. Make sure .env.claude exists with credentials."
      );
    }

    // Navigate to login page
    await page.goto("/login");

    // Verify we're on the login page
    await expect(page.locator("h1")).toHaveText("Welcome back");

    // Fill in credentials
    await page.fill("#email", email);
    await page.fill("#password", password);

    // Submit the form
    await page.click('button[type="submit"]');

    // Wait for navigation to my-projects page
    await expect(page).toHaveURL(/\/my-projects/);
  });

  test("should show error with invalid credentials", async ({ page }) => {
    await page.goto("/login");

    await page.fill("#email", "invalid@example.com");
    await page.fill("#password", "wrongpassword");

    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator(".bg-red-50")).toBeVisible();
    await expect(page.locator(".bg-red-50")).toContainText(/invalid|failed|unauthorized/i);
  });

  test("should navigate to register page", async ({ page }) => {
    await page.goto("/login");

    await page.click('a[href="/register"]');

    await expect(page).toHaveURL(/\/register/);
  });
});
