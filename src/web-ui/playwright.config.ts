import { defineConfig, devices } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// Load credentials from .env.claude if it exists
const envClaudePath = path.resolve(__dirname, "../../.env.claude");
if (fs.existsSync(envClaudePath)) {
  const envContent = fs.readFileSync(envClaudePath, "utf-8");
  for (const line of envContent.split("\n")) {
    const match = line.match(/^export\s+(\w+)=(.*)$/);
    if (match) {
      process.env[match[1]] = match[2];
    }
  }
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: process.env.TEST_APP_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
