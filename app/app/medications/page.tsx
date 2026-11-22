"use client";
import { useEffect, useState } from "react";
import { Plus, ShieldAlert, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, Field, Input, Select, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

type Med = { name: string; dosage: string; frequency: string; duration: string; warnings?: string[]; source_line?: string };
type Review = { warnings: { type: string; severity: string; message: string }[]; interactions: { drugs: string[]; severity: string; summary: string; source: { name: string; url: string } }[];
  coverage_note: string; pharmacist_notice: Record<string, string>; drug_information: { name: string; status: string; source: string; labels?: { title: string; url: string; published?: string }[] }[]; prescription_id?: string };
const sev = (s: string) => (s === "critical" ? "danger" : s === "warning" ? "warn" : "info") as "danger" | "warn" | "info";

export default function MedicationsPage() {
  const { t, locale } = useI18n();
  const sb = createClient();
  const [meds, setMeds] = useState<Med[]>([{ name: "", dosage: "", frequency: "", duration: "" }]);
  const [docId, setDocId] = useState<string>("");
  const [rxDocs, setRxDocs] = useState<{ id: string; original_name: string }[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [rev, setRev] = useState<Review | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState<{ id: string; name: string; dosage: string | null; frequency: string | null; verified: boolean }[]>([]);
  const loadSaved = () => sb.from("medication_records").select("id,name,dosage,frequency,verified").eq("active", true).order("created_at", { ascending: false }).then(({ data }) => setSaved(data ?? []));
  useEffect(() => {
    loadSaved();
    sb.from("medical_documents").select("id,original_name").eq("doc_type", "prescription").then(({ data }) => setRxDocs(data ?? []));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function importOcr(id: string) {
    setDocId(id); if (!id) return;
    const { data } = await sb.from("medical_analysis_reports").select("extracted").eq("document_id", id).order("created_at", { ascending: false }).limit(1);
    const list = data?.[0]?.extracted?.medications ?? [];
    if (list.length) setMeds(list.map((m: any) => ({ name: m.name ?? "", dosage: m.dosage ?? "", frequency: m.frequency ?? "", duration: m.duration ?? "", warnings: m.warnings, source_line: m.source_line })));
    else setErr("Analyze the prescription in Documents first (no OCR result found).");
  }
  const payload = (save: boolean) => ({ document_id: docId || null, user_confirmed: confirmed, save,
    medications: meds.filter((m) => m.name.trim() || m.source_line).map((m) => ({ name: m.name.trim() || null, dosage: m.dosage || null, frequency: m.frequency || null, duration: m.duration || null, source_line: m.source_line ?? null, warnings: m.warnings ?? [] })) });
  async function run(save: boolean) {
    setBusy(true); setErr("");
    try { const r = await api<Review>("/api/prescriptions/review", { method: "POST", json: payload(save) }); setRev(r); if (save) { loadSaved(); } }
    catch (e) { setErr(e instanceof ApiError ? e.message : t("errorGeneric")); } finally { setBusy(false); }
  }
  const upd = (i: number, k: keyof Med, v: string) => setMeds((m) => m.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-extrabold">{t("medsTitle")}</h1><p className="text-sm text-muted">{t("medsIntro")}</p></div>
      <Alert tone="danger" className="flex items-start gap-2"><ShieldAlert className="mt-0.5 shrink-0" size={18} />{t("pharmacistNotice")}</Alert>
      <Card className="space-y-4">
        {rxDocs.length > 0 && <Field label={`${t("t_prescription")} (OCR)`}><Select value={docId} onChange={(e) => importOcr(e.target.value)}><option value="">—</option>{rxDocs.map((d) => <option key={d.id} value={d.id}>{d.original_name}</option>)}</Select></Field>}
        {meds.map((m, i) => (
          <div key={i} className="space-y-2 rounded-xl border border-border p-3">
            <div className="grid gap-2 sm:grid-cols-4">
              <Field label={t("medName")}><Input value={m.name} onChange={(e) => upd(i, "name", e.target.value)} dir="ltr" data-testid={`med-name-${i}`} /></Field>
              <Field label={t("dosage")}><Input value={m.dosage} onChange={(e) => upd(i, "dosage", e.target.value)} dir="ltr" /></Field>
              <Field label={t("frequency")}><Input value={m.frequency} onChange={(e) => upd(i, "frequency", e.target.value)} /></Field>
              <Field label={t("duration")}><Input value={m.duration} onChange={(e) => upd(i, "duration", e.target.value)} /></Field>
            </div>
            {m.source_line && <p className="text-xs text-muted" dir="ltr">OCR: “{m.source_line}”</p>}
            {m.warnings?.map((w) => <p key={w} className="text-xs text-warn">⚠ {w}</p>)}
            {meds.length > 1 && <Button size="sm" variant="ghost" onClick={() => setMeds((x) => x.filter((_, j) => j !== i))}><Trash2 size={14} />{t("delete")}</Button>}
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={() => setMeds((m) => [...m, { name: "", dosage: "", frequency: "", duration: "" }])}><Plus size={14} />{t("addMed")}</Button>
        {err && <Alert tone="danger">{err}</Alert>}
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => run(false)} disabled={busy} data-testid="med-review">{busy && <Spinner />}{t("review")}</Button>
        </div>
      </Card>
      {rev && (
        <Card className="space-y-4" data-testid="med-result">
          {rev.warnings.length === 0 && <Alert tone="ok">—</Alert>}
          <ul className="space-y-2">{rev.warnings.map((w, i) => <li key={i}><Alert tone={w.severity === "critical" ? "danger" : w.severity === "warning" ? "warn" : "info"}><Badge tone={sev(w.severity)} className="me-2">{w.type}</Badge>{w.message}</Alert></li>)}</ul>
          {rev.interactions.length > 0 && (<div><h2 className="mb-1 font-bold">{t("interactions")}</h2>
            <ul className="space-y-2">{rev.interactions.map((x, i) => <li key={i}><Alert tone="warn"><b>{x.drugs.join(" + ")}</b> ({x.severity}) — {x.summary} <a className="text-brand underline" href={x.source.url} target="_blank" rel="noopener noreferrer">{x.source.name}</a></Alert></li>)}</ul></div>)}
          <p className="text-xs text-muted">{t("curated")}</p>
          <div><h2 className="mb-1 font-bold">{t("drugInfo")}</h2>
            <ul className="space-y-1 text-sm">{rev.drug_information.map((d) => <li key={d.name}><b dir="ltr">{d.name}</b>: {d.status === "ok" ? d.labels?.slice(0, 2).map((l) => <a key={l.url} className="me-2 text-brand underline" href={l.url} target="_blank" rel="noopener noreferrer">{l.title.slice(0, 60)}…</a>) : <span className="text-muted">{t("unavailable")}</span>}</li>)}</ul></div>
          <Alert tone="danger">{rev.pharmacist_notice[locale]}</Alert>
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} data-testid="med-confirm" /><span>{t("confirmOcr")}</span></label>
          <Button onClick={() => run(true)} disabled={!confirmed || busy} data-testid="med-save">{t("saveMeds")}</Button>
          {rev.prescription_id && <Alert tone="ok">{t("saved")}</Alert>}
        </Card>
      )}
      <Card><h2 className="mb-2 font-bold">{t("myMeds")}</h2>
        {saved.length === 0 ? <p className="text-sm text-muted">—</p> : <ul className="divide-y divide-border text-sm">{saved.map((m) => <li key={m.id} className="flex justify-between py-2"><span dir="ltr" className="font-medium">{m.name}</span><span className="text-muted" dir="ltr">{[m.dosage, m.frequency].filter(Boolean).join(" · ") || "—"}</span></li>)}</ul>}
      </Card>
    </div>
  );
}
