import { test, expect, type Browser, type Page } from "@playwright/test";
import { allowLeavingTheEditor, editorBody } from "./helpers";

/*
 * An article published under a person's own name, end to end: U writes and
 * publishes one from their profile; V follows U first, then sees the article
 * in Latest flagged with U's name, opens it at /users/{U.id}/articles/{slug},
 * and finds it in the bell.
 *
 * Two logins in all (U and V), well under the 5/min login limit. Serial: the
 * steps build on each other and share the two pages. V is a seed user
 * (`make seed`, password "123"); U is the bootstrap test user from .env.claude.
 */
test.describe.configure({ mode: "serial" });

// The dev server compiles each route on its first visit, which can take longer
// than Playwright's default 5s; every first arrival on a page waits this long.
const FIRST_VISIT = { timeout: 60_000 };

const SEED_PASSWORD = "123";
const V_EMAIL = process.env.TEST_FOLLOWER_EMAIL ?? "bjarki@example.com";

interface Me {
  id: string;
}

// The backend's origin, learned from the login request the page makes: `make
// dev` picks a free port, so a hard-coded origin is wrong whenever 8000 is
// taken by something else.
async function loginAs(page: Page, email: string, password: string): Promise<string> {
  const loginResponse = page.waitForResponse((r) => r.url().endsWith("/api/auth/login"));
  await page.goto("/login");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  const response = await loginResponse;
  expect(response.ok(), `login as ${email}`).toBe(true);
  await expect(page).toHaveURL(/\/(my-projects|onboarding)/);
  return new URL(response.url()).origin;
}

function authed(page: Page, apiUrl: string) {
  return <T>(path: string, init: RequestInit = {}) =>
    page.evaluate(
      async ({ apiUrl, path, init }) => {
        const response = await fetch(`${apiUrl}${path}`, {
          ...init,
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            "Content-Type": "application/json",
            ...(init.headers ?? {}),
          },
        });
        return response.status === 204 ? null : response.json();
      },
      { apiUrl, path, init },
    ) as Promise<T>;
}

test.describe("Author-owned article", () => {
  test.setTimeout(120_000);

  let u: Page;
  let v: Page;
  let apiUrl: string;
  let uId: string;
  let articleId: string;
  let slug: string;
  const title = `Lab notebook ${Date.now()}`;

  test.beforeAll(async ({ browser }: { browser: Browser }) => {
    const uPassword = process.env.TEST_USER_PASSWORD;
    if (!uPassword) {
      throw new Error("TEST_USER_PASSWORD not set. Make sure .env.claude exists with credentials.");
    }
    u = await (await browser.newContext()).newPage();
    v = await (await browser.newContext()).newPage();
    allowLeavingTheEditor(u);

    apiUrl = await loginAs(u, process.env.TEST_USER_EMAIL ?? "test@example.com", uPassword);
    uId = (await authed(u, apiUrl)<Me>("/api/auth/me")).id;
    await loginAs(v, V_EMAIL, SEED_PASSWORD);
  });

  test.afterAll(async () => {
    const call = authed(u, apiUrl);
    if (articleId) await call(`/api/articles/${articleId}`, { method: "DELETE" });
    await authed(v, apiUrl)(`/api/users/${uId}/follow`, { method: "DELETE" });
    await u.context().close();
    await v.context().close();
  });

  test("U starts an article from their own profile", async () => {
    await u.goto(`/users/${uId}`);
    await u.getByRole("button", { name: "Write article" }).click(FIRST_VISIT);

    await expect(u).toHaveURL(/\/articles\/edit\/[0-9a-f-]+$/, FIRST_VISIT);
    articleId = u.url().split("/").pop()!;
    // No project, so no channel to choose; the breadcrumb leads home.
    await expect(u.getByLabel("Channel")).toHaveCount(0);
    await expect(u.getByRole("link", { name: "Your profile" })).toBeVisible(FIRST_VISIT);
  });

  test("V follows U before anything is published", async () => {
    await v.goto(`/users/${uId}`);
    await v.getByRole("button", { name: "Follow", exact: true }).click(FIRST_VISIT);
    await expect(v.getByRole("button", { name: "Following" })).toBeVisible();

    await v.reload();
    await expect(v.getByRole("button", { name: "Following" })).toBeVisible(FIRST_VISIT);
  });

  test("U publishes and lands back on their profile with a Published badge", async () => {
    await u.fill('input[placeholder="Article title"]', title);
    await editorBody(u).click();
    await u.keyboard.type("Write the date, write what you tried, write what happened.");

    await u.getByRole("button", { name: "Publish", exact: true }).click();
    await u.getByRole("dialog").getByRole("button", { name: "Publish", exact: true }).click();

    await expect(u).toHaveURL(new RegExp(`/users/${uId}$`), FIRST_VISIT);
    const row = u.locator('[data-testid="own-articles"] li', { hasText: title });
    await expect(row.getByTestId("article-badge")).toHaveText("Published");

    const mine = await authed(u, apiUrl)<Array<{ id: string; slug: string | null }>>(
      "/api/auth/me/articles",
    );
    slug = mine.find((a) => a.id === articleId)?.slug ?? "";
    expect(slug).not.toBe("");
  });

  test("V sees it in Latest flagged with U's name", async () => {
    await v.goto("/latest");
    const entry = v.locator("main article", { hasText: title }).first();
    await expect(entry).toBeVisible(FIRST_VISIT);
    await expect(entry).toContainText("Test User");
    await expect(entry.getByRole("link").first()).toHaveAttribute(
      "href",
      new RegExp(`/users/${uId}/articles/${slug}`),
    );
  });

  // Before the article is opened: reading it marks its notification read, so
  // the bell has to be checked first.
  test("V finds it in the bell", async () => {
    await v.goto("/notifications");
    await expect(v.locator("main")).toContainText(title, FIRST_VISIT);
    await expect(v.locator("main")).toContainText("Test User published");
  });

  test("V opens it under U's profile", async () => {
    await v.goto(`/users/${uId}/articles/${slug}`);
    await expect(v.getByRole("heading", { level: 1 })).toHaveText(title, FIRST_VISIT);
    await expect(v.getByTestId("article-container")).toContainText("Test User");
    await expect(v.getByTestId("article-container")).toHaveAttribute("href", `/users/${uId}`);
  });
});
