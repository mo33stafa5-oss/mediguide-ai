// Captures REAL screenshots of the running app for the presentation (no mock-ups).
import { chromium } from "@playwright/test";
import fs from "node:fs";
const OUT = "docs/presentation/screenshots";
const SUPA = "http://127.0.0.1:54321", SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "", PW = "Passw0rd-shot1";
const H = { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" };
async function user(role) {
  const email = `shot${Date.now()}${role ?? "p"}@example.test`;
  const u = await (await fetch(`${SUPA}/auth/v1/admin/users`, { method: "POST", headers: H, body: JSON.stringify({ email, password: PW, email_confirm: true, user_metadata: { full_name: role ? "Admin Demo" : "Demo Patient (synthetic)" } }) })).json();
  if (role) await fetch(`${SUPA}/rest/v1/profiles?id=eq.${u.id}`, { method: "PATCH", headers: H, body: JSON.stringify({ role }) });
  return email;
}
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
async function login(page, email) {
  await page.goto("http://localhost:3000/login");
  await page.locator('input[type="email"]').fill(email); await page.locator('input[type="password"]').fill(PW);
  await page.locator('form button[type="submit"]').click(); await page.waitForURL(/\/app/);
}
const ctx = await browser.newContext({ viewport: { width: 1360, height: 860 }, deviceScaleFactor: 1.5 });
const page = await ctx.newPage();
await page.goto("http://localhost:3000/"); await page.screenshot({ path: `${OUT}/01_landing_ar.png` });
await page.locator("[data-testid=lang-toggle]:visible").first().click(); await page.waitForTimeout(300); await page.screenshot({ path: `${OUT}/02_landing_en.png` });
const email = await user();
await page.locator("[data-testid=lang-toggle]:visible").first().click();
await login(page, email);
// create real data: risk assessment, lab document analysed, medication review
await page.goto("http://localhost:3000/app/risk");
const nums = page.locator('input[type="number"]');
for (const [i, v] of ["63", "145", "233", "150", "2.3", "0"].entries()) await nums.nth(i).fill(v);
await page.getByTestId("risk-submit").click(); await page.getByTestId("risk-result").waitFor();
await page.locator("[data-testid=lang-toggle]:visible").first().click(); await page.waitForTimeout(300);
await page.screenshot({ path: `${OUT}/05_risk_result_en.png`, fullPage: true });
await page.locator("[data-testid=lang-toggle]:visible").first().click();
await page.goto("http://localhost:3000/app/documents");
const png = Buffer.from(await page.evaluate(() => { const c = document.createElement("canvas"); c.width = 1400; c.height = 800; const x = c.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, 1400, 800); x.fillStyle = "#000"; x.font = "40px sans-serif";
  ["Lipid Panel  Date: 2026-03-02", "Total Cholesterol 245 mg/dL (125 - 200)", "HDL 38 mg/dL (40 - 60)", "Glucose 92 mg/dL (70 - 99)"].forEach((l, i) => x.fillText(l, 40, 80 + i * 70)); return c.toDataURL("image/png").split(",")[1]; }), "base64");
await page.getByTestId("doc-file").setInputFiles({ name: "synthetic_lab.png", mimeType: "image/png", buffer: png });
await page.getByTestId("doc-upload").click();
const row = page.getByTestId("doc-table").locator("tbody tr").first(); await row.waitFor();
await row.getByRole("button", { name: /تحليل|analyze/i }).click(); await page.getByTestId("report").waitFor({ timeout: 60000 });
await page.screenshot({ path: `${OUT}/06_documents_ocr.png`, fullPage: true });
await page.goto("http://localhost:3000/app/medications");
await page.getByTestId("med-name-0").fill("warfarin");
await page.getByRole("button", { name: /إضافة دواء|add medication/i }).click(); await page.getByTestId("med-name-1").fill("ibuprofen");
await page.getByTestId("med-review").click(); await page.getByTestId("med-result").waitFor();
await page.screenshot({ path: `${OUT}/07_medication_review.png`, fullPage: true });
await page.goto("http://localhost:3000/app/chat"); await page.getByTestId("consent-btn").waitFor(); await page.screenshot({ path: `${OUT}/04_chat_consent_gate.png` });
await page.goto("http://localhost:3000/app"); await page.waitForTimeout(800); await page.screenshot({ path: `${OUT}/03_dashboard.png` });
await page.locator("[data-testid=theme-toggle]:visible").first().click(); await page.waitForTimeout(300); await page.screenshot({ path: `${OUT}/08_dashboard_dark.png` });
const admin = await user("admin"); const p2 = await (await browser.newContext({ viewport: { width: 1360, height: 860 }, deviceScaleFactor: 1.5 })).newPage();
await login(p2, admin); await p2.goto("http://localhost:3000/app/admin"); await p2.getByTestId("tab-evaluation").click(); await p2.waitForTimeout(1200);
await p2.screenshot({ path: `${OUT}/09_admin_evaluation.png`, fullPage: true });
await p2.getByTestId("tab-system").click(); await p2.waitForTimeout(1000); await p2.screenshot({ path: `${OUT}/10_admin_system.png` });
const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true }); const mp = await m.newPage();
await login(mp, email); await mp.goto("http://localhost:3000/app"); await mp.waitForTimeout(800); await mp.screenshot({ path: `${OUT}/11_mobile_dashboard.png` });
await browser.close(); console.log(fs.readdirSync(OUT));
