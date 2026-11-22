import { test, expect } from "@playwright/test";
import { createUser, login, textPng } from "./helpers";

test("heart risk form validates and returns a model result with limitations", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/risk");
  await page.getByTestId("risk-submit").click(); // empty required numbers -> validation, no request
  await expect(page.getByTestId("risk-result")).toHaveCount(0);
  const nums = page.locator('input[type="number"]');
  for (const [i, v] of ["63", "145", "233", "150", "2.3", "0"].entries()) await nums.nth(i).fill(v);
  await page.getByTestId("risk-submit").click();
  const r = page.getByTestId("risk-result");
  await expect(r).toBeVisible();
  await expect(r).toContainText("mediguide-heart-1.0.0");
  await expect(r).toContainText("%");
});

test("document upload with preview, OCR analysis of a lab report, signed URL and deletion", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/documents");
  const png = await textPng(page, ["Lipid Panel  Date: 2026-03-02", "Total Cholesterol 245 mg/dL (125 - 200)", "HDL 38 mg/dL (40 - 60)", "Glucose 92 mg/dL (70 - 99)"]);
  await page.getByTestId("doc-file").setInputFiles({ name: "lab.png", mimeType: "image/png", buffer: png });
  await expect(page.locator('img[alt="preview"]')).toBeVisible();
  await page.getByTestId("doc-upload").click();
  const row = page.getByTestId("doc-table").locator("tbody tr").first();
  await expect(row).toContainText("lab.png");
  await row.getByRole("button", { name: /تحليل|analyze/i }).click();
  const rep = page.getByTestId("report");
  await expect(rep).toBeVisible({ timeout: 60_000 });
  await expect(rep).toContainText("245");
  await expect(rep).toContainText(/مرتفع|High/);
  const [popup] = await Promise.all([page.waitForEvent("popup"), row.getByRole("button", { name: "file" }).click()]);
  expect(popup.url()).toContain("token=");
  await popup.close();
  page.once("dialog", (d) => d.accept());
  await row.getByRole("button", { name: /حذف|delete/i }).click();
  await expect(page.getByTestId("doc-table").locator("tbody tr")).toHaveCount(0);
});

test("rejects a fake image file", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/documents");
  await page.getByTestId("doc-file").setInputFiles({ name: "evil.png", mimeType: "image/png", buffer: Buffer.from("MZ not an image".repeat(40)) });
  await page.getByTestId("doc-upload").click();
  await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)').first()).toBeVisible();
});

test("medication review shows interaction and requires confirmation to save", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/medications");
  await page.getByTestId("med-name-0").fill("warfarin");
  await page.getByRole("button", { name: /إضافة دواء|add medication/i }).click();
  await page.getByTestId("med-name-1").fill("ibuprofen");
  await page.getByTestId("med-review").click();
  const res = page.getByTestId("med-result");
  await expect(res).toContainText("ibuprofen + warfarin");
  await expect(res).toContainText(/pharmacist|الصيدلي/);
  await expect(page.getByTestId("med-save")).toBeDisabled();
  await page.getByTestId("med-confirm").check();
  await page.getByTestId("med-save").click();
  await expect(page.getByText("warfarin", { exact: true }).last()).toBeVisible();
});

test("chat: consent gate then clear 'not configured' message without Gemini key", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/chat");
  await page.getByTestId("consent-btn").click();
  await page.getByTestId("chat-input").fill("What is LDL cholesterol?");
  await page.getByTestId("chat-send").click();
  await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)').first()).toContainText(/غير مُفعّلة|not configured/);
});

test("profile save and allergy persistence", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/profile");
  await page.getByTestId("allergies").fill("penicillin, aspirin");
  await page.getByTestId("profile-save").click();
  await expect(page.locator('[role="status"]').first()).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("allergies")).toHaveValue("penicillin, aspirin");
});

test("patient cannot use admin area", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await expect(page.getByRole("link", { name: /الإدارة|admin/i })).toHaveCount(0);
  await page.goto("/app/admin");
  await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)').first()).toBeVisible();
});

test("admin sees system tab and cannot see patient private data", async ({ page }) => {
  const a = await createUser(undefined, "admin");
  await login(page, a.email);
  await page.goto("/app/admin");
  await expect(page.getByTestId("tab-users")).toBeVisible();
  await page.getByTestId("tab-evaluation").click();
  await expect(page.getByText("mediguide-heart-1.0.0").first()).toBeVisible();
  await page.getByTestId("tab-users").click();
  await expect(page.locator("table tbody tr").first()).toBeVisible();
});

test("account deletion removes the account", async ({ page }) => {
  const u = await createUser();
  await login(page, u.email);
  await page.goto("/app/profile");
  await expect(page.getByTestId("delete-account")).toBeDisabled();
  await page.getByTestId("delete-confirm").fill("DELETE");
  await page.getByTestId("delete-account").click();
  await expect(page).toHaveURL("http://localhost:3000/");
  await page.goto("/login");
  await page.getByLabel(/البريد|email/i).fill(u.email);
  await page.locator('input[type="password"]').fill("Passw0rd-e2e1");
  await page.locator('form button[type="submit"]').click();
  await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)').first()).toBeVisible();
});
