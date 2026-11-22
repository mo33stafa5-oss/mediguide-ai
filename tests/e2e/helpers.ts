import { expect, type Page } from "@playwright/test";

export const SUPA = "http://127.0.0.1:54321";
export const SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
export const MAIL = "http://127.0.0.1:54324";
export const PASSWORD = "Passw0rd-e2e1";

export const uniq = () => `e2e${Date.now()}${Math.floor(Math.random() * 1e4)}@example.test`;

/** Creates a confirmed user directly with the admin API (fast path for tests that are not about sign-up). */
export async function createUser(email = uniq(), role?: string, consentAi = false) {
  const r = await fetch(`${SUPA}/auth/v1/admin/users`, {
    method: "POST", headers: { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: PASSWORD, email_confirm: true, user_metadata: { full_name: "مريض تجريبي", consent_terms: "true" } }),
  });
  const u = await r.json();
  const patch: Record<string, unknown> = {};
  if (role) patch.role = role;
  if (consentAi) patch.consent_ai_processing_at = new Date().toISOString();
  if (Object.keys(patch).length)
    await fetch(`${SUPA}/rest/v1/profiles?id=eq.${u.id}`, { method: "PATCH", headers: { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" }, body: JSON.stringify(patch) });
  return { email, id: u.id as string };
}

export async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel(/email|البريد/i).fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
}

/** Minimal valid PNG with drawn text is produced by Python in tests; here we generate via the browser canvas instead. */
export async function textPng(page: Page, lines: string[]): Promise<Buffer> {
  const b64 = await page.evaluate((ls) => {
    const c = document.createElement("canvas"); c.width = 1400; c.height = 800;
    const x = c.getContext("2d")!; x.fillStyle = "#fff"; x.fillRect(0, 0, c.width, c.height); x.fillStyle = "#000"; x.font = "40px sans-serif";
    ls.forEach((l, i) => x.fillText(l, 40, 80 + i * 70));
    return c.toDataURL("image/png").split(",")[1];
  }, lines);
  return Buffer.from(b64, "base64");
}
