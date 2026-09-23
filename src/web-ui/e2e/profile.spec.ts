import { test, expect, type Page } from "@playwright/test";
import { API_URL, login } from "./helpers";

// One login for the file: /api/auth/login allows 5/min per IP.
test.describe.configure({ mode: "serial" });

interface Me {
  id: string;
  first_name: string;
  last_name: string;
  info: string;
}

// The signed-in user's own row, straight from the API: the specs need the id
// to reach the public page, and the original About text to put back.
async function fetchMe(page: Page): Promise<Me> {
  return page.evaluate(
    async ({ apiUrl }) =>
      fetch(`${apiUrl}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      }).then((r) => r.json()),
    { apiUrl: API_URL },
  );
}

async function restoreAbout(page: Page, info: string) {
  await page.evaluate(
    async ({ apiUrl, info }) =>
      fetch(`${apiUrl}/api/auth/me`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ info }),
      }),
    { apiUrl: API_URL, info },
  );
}

test.describe("User profile", () => {
  let page: Page;
  let me: Me;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await login(page);
    me = await fetchMe(page);
  });

  test.afterAll(async () => {
    await restoreAbout(page, me.info);
    await page.close();
  });

  test("the public page shows the person, their projects and articles", async () => {
    await page.goto(`/users/${me.id}`);

    const name = [me.first_name, me.last_name].filter(Boolean).join(" ") || "Anonymous";
    await expect(page.locator("h1")).toHaveText(name);
    await expect(page.getByTestId("profile-meta")).toContainText(/Joined .+ · \d+ projects? · \d+ articles?/);
    await expect(page.getByRole("heading", { name: "About" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Articles" })).toBeVisible();
    // Own profile: the way back to the editor.
    await expect(page.getByRole("link", { name: "Edit profile" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  test("editing the About text round-trips to the public page", async () => {
    const marker = `Edited by Playwright at ${Date.now()}`;

    await page.goto("/profile");
    await expect(page.locator("h1")).toHaveText("Edit profile");
    await page.fill("#info", marker);

    const saved = page.waitForResponse(
      (r) => r.url().endsWith("/api/auth/me") && r.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Save changes" }).click();
    await saved;

    await expect(page).toHaveURL(new RegExp(`/users/${me.id}$`));
    await expect(page.getByTestId("profile-about")).toContainText(marker);
  });

  test("the public page's About is the editor's Preview", async () => {
    await page.goto("/profile");
    await page.fill("#info", "Plain **bold** ![pic](https://example.com/a.png)");
    await page.getByRole("tab", { name: "Preview" }).click();

    const preview = page.getByTestId("about-preview");
    await expect(preview.locator("strong")).toHaveText("bold");
    await expect(preview.locator("img")).toHaveCount(0);
  });

  test("account settings live on their own page", async () => {
    await page.goto("/profile");
    await expect(page.locator("#info")).toBeVisible();
    await expect(page.getByText("Discussion emails")).toHaveCount(0);

    await page.getByRole("link", { name: /Account settings/ }).click();
    await expect(page).toHaveURL(/\/profile\/settings$/);
    await expect(page.getByText("Discussion emails")).toBeVisible();
  });

  test("a made-up id is User not found", async () => {
    await page.goto("/users/00000000-0000-0000-0000-000000000000");
    await expect(page.locator("h1")).toHaveText("User not found");
  });
});
