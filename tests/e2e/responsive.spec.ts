import { test, expect } from "@playwright/test";
import { createUser, login } from "./helpers";

test("mobile: landing has no horizontal overflow, RTL, bottom nav in app", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  const u = await createUser();
  await login(page, u.email);
  await expect(page.getByRole("navigation", { name: "Mobile" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await page.goto("/app/risk");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
