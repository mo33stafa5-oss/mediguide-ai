"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMe } from "@/components/app-shell";
import { Alert, Button, Card, Field, Input, Select, Textarea } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean).slice(0, 30);

export default function ProfilePage() {
  const { t, locale, setLocale } = useI18n();
  const me = useMe();
  const sb = createClient();
  const router = useRouter();
  const [f, setF] = useState({ full_name: me.full_name, date_of_birth: "", sex: "", height_cm: "", weight_kg: "", blood_type: "", allergies: "", chronic_conditions: "", family_history: "", smoker: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [confirmText, setConfirmText] = useState("");
  useEffect(() => {
    sb.from("user_medical_profiles").select("*").eq("user_id", me.id).maybeSingle().then(({ data: d }) => {
      if (d) setF((p) => ({ ...p, date_of_birth: d.date_of_birth ?? "", sex: d.sex ?? "", height_cm: d.height_cm ?? "", weight_kg: d.weight_kg ?? "", blood_type: d.blood_type ?? "",
        allergies: (d.allergies ?? []).join(", "), chronic_conditions: (d.chronic_conditions ?? []).join(", "), family_history: d.family_history ?? "", smoker: d.smoker == null ? "" : String(d.smoker) }));
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));
  async function save() {
    setMsg(null);
    const a = await sb.from("profiles").update({ full_name: f.full_name.slice(0, 200), locale }).eq("id", me.id);
    const b = await sb.from("user_medical_profiles").upsert({
      user_id: me.id, date_of_birth: f.date_of_birth || null, sex: f.sex || null, height_cm: f.height_cm === "" ? null : Number(f.height_cm), weight_kg: f.weight_kg === "" ? null : Number(f.weight_kg),
      blood_type: f.blood_type || null, allergies: csv(f.allergies), chronic_conditions: csv(f.chronic_conditions), family_history: f.family_history, smoker: f.smoker === "" ? null : f.smoker === "true" });
    const e = a.error ?? b.error;
    setMsg(e ? { ok: false, text: e.message } : { ok: true, text: t("saved") });
  }
  async function exportData() {
    const d = await api("/api/account/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }));
    const a = document.createElement("a"); a.href = url; a.download = "mediguide-data.json"; a.click(); URL.revokeObjectURL(url);
  }
  async function del() {
    try { await api("/api/account", { method: "DELETE" }); await sb.auth.signOut(); router.replace("/"); router.refresh(); }
    catch (e) { setMsg({ ok: false, text: e instanceof ApiError ? e.message : t("errorGeneric") }); }
  }
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-extrabold">{t("profileTitle")}</h1>
      <Card className="grid gap-4 sm:grid-cols-2">
        <Field label={t("fullName")}><Input value={f.full_name} onChange={set("full_name")} /></Field>
        <Field label={t("email")}><Input value={me.email} disabled dir="ltr" /></Field>
        <Field label={t("language")}><Select value={locale} onChange={(e) => setLocale(e.target.value as "ar" | "en")}><option value="ar">العربية</option><option value="en">English</option></Select></Field>
        <Field label={t("dob")}><Input type="date" value={f.date_of_birth} onChange={set("date_of_birth")} /></Field>
        <Field label={t("f_sex")}><Select value={f.sex} onChange={set("sex")}><option value="">—</option><option value="male">{t("male")}</option><option value="female">{t("female")}</option></Select></Field>
        <Field label={t("bloodType")}><Select value={f.blood_type} onChange={set("blood_type")}><option value="">—</option>{["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((b) => <option key={b}>{b}</option>)}</Select></Field>
        <Field label={t("height")}><Input type="number" value={f.height_cm} onChange={set("height_cm")} /></Field>
        <Field label={t("weight")}><Input type="number" value={f.weight_kg} onChange={set("weight_kg")} /></Field>
        <Field label={t("smoker")}><Select value={f.smoker} onChange={set("smoker")}><option value="">—</option><option value="true">{t("yes")}</option><option value="false">{t("no")}</option></Select></Field>
        <Field label={t("allergies")}><Input value={f.allergies} onChange={set("allergies")} data-testid="allergies" /></Field>
        <div className="sm:col-span-2"><Field label={t("conditions")}><Input value={f.chronic_conditions} onChange={set("chronic_conditions")} /></Field></div>
        <div className="sm:col-span-2"><Field label={t("familyHistory")}><Textarea value={f.family_history} onChange={set("family_history")} maxLength={2000} /></Field></div>
        <div className="flex items-center gap-3 sm:col-span-2"><Button onClick={save} data-testid="profile-save">{t("save")}</Button>{msg && <Alert tone={msg.ok ? "ok" : "danger"}>{msg.text}</Alert>}</div>
      </Card>
      <Card className="space-y-3">
        <h2 className="font-bold">{t("consentTitle")}</h2>
        <p className="text-sm text-muted">{me.consent_ai ? t("consentGiven") : t("consentBody")}</p>
        <Button variant="outline" onClick={exportData}>{t("exportData")}</Button>
      </Card>
      <Card className="space-y-3 border-danger/40">
        <h2 className="font-bold text-danger">{t("deleteAccount")}</h2>
        <Alert tone="danger">{t("deleteWarn")}</Alert>
        <Field label={t("typeDelete")}><Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} dir="ltr" data-testid="delete-confirm" /></Field>
        <Button variant="danger" disabled={confirmText !== "DELETE"} onClick={del} data-testid="delete-account">{t("deleteAccount")}</Button>
      </Card>
    </div>
  );
}
