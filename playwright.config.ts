import { defineConfig, devices } from "@playwright/test";

// Expects: local Supabase (npx supabase start), API on :8000 (uvicorn), and the built app (npm run build && npm start -- -p 3000).
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "tests/e2e/results.json" }]],
  use: { baseURL: "http://localhost:3000", trace: "off", launchOptions: { executablePath: process.env.PW_CHROMIUM ?? "/opt/pw-browsers/chromium" } },
  projects: [
    { name: "desktop", testIgnore: /responsive\.spec\.ts/, use: { ...devices["Desktop Chrome"], launchOptions: { executablePath: process.env.PW_CHROMIUM ?? "/opt/pw-browsers/chromium" } } },
    { name: "mobile", testMatch: /responsive\.spec\.ts/, use: { ...devices["Pixel 7"], launchOptions: { executablePath: process.env.PW_CHROMIUM ?? "/opt/pw-browsers/chromium" } } },
  ],
});
