import { test, expect } from "@playwright/test";
import { createUser, login, MAIL, PASSWORD, uniq } from "./helpers";

test("default language is Arabic RTL and switches to English LTR (persisted)", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("صحة قلبك");
  await page.getByTestId("lang-toggle").click();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("cardiovascular health");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr"); // cookie persisted, SSR renders English
});

test("dark mode toggle", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("theme-toggle").click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("protected routes redirect to login when signed out", async ({ page }) => {
  await page.goto("/app/documents");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fdocuments/);
});

test("registration -> email verification -> login -> logout", async ({ page, request }) => {
  const email = uniq();
  await page.goto("/register");
  await page.getByLabel(/الاسم|name/i).fill("Test Patient");
  await page.getByLabel(/البريد|email/i).fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByText("consentTerms").first()).toHaveCount(0); // key never leaks
  await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)').first()).toBeVisible(); // consent checkbox required
  await page.locator('input[type="checkbox"]').check();
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("check-email")).toBeVisible();

  // unverified users cannot sign in
  await page.goto("/login");
  await page.getByLabel(/البريد|email/i).fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/login/);

  // follow the real verification email from Mailpit
  let link = "";
  for (let i = 0; i < 20 && !link; i++) {
    const list = await (await request.get(`${MAIL}/api/v1/search?query=to:${encodeURIComponent(email)}`)).json();
    if (list.messages?.length) {
      const msg = await (await request.get(`${MAIL}/api/v1/message/${list.messages[0].ID}`)).json();
      link = (msg.HTML as string).match(/href="([^"]+)"/)?.[1]?.replace(/&amp;/g, "&") ?? "";
    } else await page.waitForTimeout(500);
  }
  expect(link).toContain("/auth/v1/verify");
  await page.goto(link);
  await expect(page).toHaveURL(/\/app/);
  await page.getByRole("button", { name: /تسجيل الخروج|sign out/i }).first().click();
  await expect(page).toHaveURL("http://localhost:3000/");
});

test("login with wrong password shows error; correct one reaches dashboard", async ({ page }) => {
  const u = await createUser();
  await page.goto("/login");
  await page.getByLabel(/البريد|email/i).fill(u.email);
  await page.locator('input[type="password"]').fill("WrongPass123");
  await page.locator('form button[type="submit"]').click();
  await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)').first()).toBeVisible();
  await login(page, u.email);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("مرحبًا");
});

test("password recovery email is sent", async ({ page, request }) => {
  const u = await createUser();
  await page.goto("/forgot-password");
  await page.locator('input[type="email"]').fill(u.email);
  await page.locator('form button[type="submit"]').click();
  await expect(page.locator('[role="status"]')).toBeVisible();
  let found = false;
  for (let i = 0; i < 20 && !found; i++) {
    const list = await (await request.get(`${MAIL}/api/v1/search?query=to:${encodeURIComponent(u.email)}`)).json();
    found = list.messages?.length > 0 || false;
    if (!found) await page.waitForTimeout(500);
  }
  expect(found).toBe(true);
});
