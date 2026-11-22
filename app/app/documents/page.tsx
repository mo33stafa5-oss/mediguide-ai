"use client";
import { useCallback, useEffect, useState } from "react";
import { FileText, Eye, Trash2, Upload, Wand2 } from "lucide-react";
import { Alert, Badge, Button, Card, Field, Select, Spinner } from "@/components/ui";
import { api, ApiError, uploadWithProgress } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import type { Key } from "@/lib/i18n/dict";

type Doc = { id: string; doc_type: string; original_name: string; status: string; created_at: string; mime_type: string; size_bytes: number };
type Report = { id: string; report_type: string; extracted: Record<string, any>; warnings: string[]; ocr_engine: string };
const TYPES = ["lab", "ecg", "xray", "prescription", "general"] as const;
const tone = (s: string) => (s === "failed" ? "danger" : s === "analyzed" ? "ok" : s === "needs_review" ? "warn" : "info") as "danger" | "ok" | "warn" | "info";

export default function DocumentsPage() {
  const { t, locale } = useI18n();
  const sb = createClient();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [type, setType] = useState<(typeof TYPES)[number]>("lab");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [pct, setPct] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [report, setReport] = useState<{ doc: Doc; rep: Report } | null>(null);

  const load = useCallback(async () => {
    const { data } = await sb.from("medical_documents").select("id,doc_type,original_name,status,created_at,mime_type,size_bytes").order("created_at", { ascending: false });
    setDocs(data ?? []);
  }, [sb]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (file?.type.startsWith("image/")) { const u = URL.createObjectURL(file); setPreview(u); return () => URL.revokeObjectURL(u); } setPreview(null); }, [file]);

  async function doUpload() {
    if (!file) return;
    setErr(""); setPct(0);
    const fd = new FormData(); fd.append("file", file); fd.append("doc_type", type);
    try { await uploadWithProgress("/api/documents/upload", fd, setPct); setFile(null); await load(); }
    catch (e) { setErr(e instanceof ApiError ? e.message : t("errorGeneric")); } finally { setPct(null); }
  }
  async function showReport(d: Doc) {
    const { data } = await sb.from("medical_analysis_reports").select("*").eq("document_id", d.id).order("created_at", { ascending: false }).limit(1);
    if (data?.[0]) setReport({ doc: d, rep: data[0] as Report });
  }
  async function analyze(d: Doc) {
    setBusyId(d.id); setErr("");
    try { await api("/api/documents/analyze", { method: "POST", json: { document_id: d.id } }); await load(); await showReport(d); }
    catch (e) { setErr(e instanceof ApiError ? (e.code === "ocr_unavailable" ? e.message : e.message) : t("errorGeneric")); await load(); } finally { setBusyId(null); }
  }
  async function view(d: Doc) { const r = await api<{ url: string }>(`/api/documents/${d.id}/url`); window.open(r.url, "_blank", "noopener,noreferrer"); }
  async function remove(d: Doc) { if (!confirm(t("confirmDelete"))) return; await api(`/api/documents/${d.id}`, { method: "DELETE" }); if (report?.doc.id === d.id) setReport(null); load(); }

  const x = report?.rep.extracted ?? {};
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-extrabold">{t("docsTitle")}</h1>
      <Card className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("docType")}><Select value={type} onChange={(e) => setType(e.target.value as typeof type)} data-testid="doc-type">{TYPES.map((k) => <option key={k} value={k}>{t(`t_${k}` as Key)}</option>)}</Select></Field>
          <Field label={t("chooseFile")}><input type="file" accept="image/jpeg,image/png,application/pdf" data-testid="doc-file" onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full rounded-xl border border-dashed border-border bg-soft p-2.5 text-sm file:me-3 file:rounded-lg file:border-0 file:bg-brand file:px-3 file:py-1.5 file:text-white" /></Field>
        </div>
        {type === "xray" && <Alert tone="warn">{t("xrayNotice")}</Alert>}
        {file && (
          <div className="flex items-center gap-3 text-sm">
            {preview ? <img src={preview} alt="preview" className="h-24 w-24 rounded-xl border border-border object-cover" /> : <FileText size={40} className="text-brand" />}
            <div><p className="font-medium">{file.name}</p><p className="text-xs text-muted">{(file.size / 1024).toFixed(0)} KB</p></div>
          </div>
        )}
        {pct !== null && <div role="progressbar" aria-valuenow={pct} className="h-2 overflow-hidden rounded-full bg-soft"><div className="gradient-brand h-full transition-all" style={{ width: `${pct}%` }} /></div>}
        {err && <Alert tone="danger">{err}</Alert>}
        <Button onClick={doUpload} disabled={!file || pct !== null} data-testid="doc-upload">{pct !== null ? <Spinner /> : <Upload size={16} />}{pct !== null ? t("uploading") : t("upload")}</Button>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm" data-testid="doc-table">
          <thead className="bg-soft text-start text-xs text-muted"><tr><th className="p-3 text-start">{t("docType")}</th><th className="p-3 text-start">File</th><th className="p-3 text-start">{t("status")}</th><th className="p-3 text-start">{t("date")}</th><th className="p-3" /></tr></thead>
          <tbody>{docs.map((d) => (
            <tr key={d.id} className="border-t border-border">
              <td className="p-3">{t(`t_${d.doc_type}` as Key)}</td><td className="max-w-40 truncate p-3" dir="ltr">{d.original_name}</td>
              <td className="p-3"><Badge tone={tone(d.status)}>{t(`s_${d.status}` as Key)}</Badge></td>
              <td className="p-3 text-xs text-muted">{new Date(d.created_at).toLocaleDateString(locale === "ar" ? "ar-EG" : "en-GB")}</td>
              <td className="flex justify-end gap-1 p-3">
                <Button size="sm" variant="outline" onClick={() => analyze(d)} disabled={busyId === d.id}>{busyId === d.id ? <Spinner /> : <Wand2 size={14} />}{t("analyze")}</Button>
                <Button size="sm" variant="ghost" onClick={() => (d.status === "uploaded" ? view(d) : showReport(d))} aria-label={t("view")}><Eye size={14} /></Button>
                <Button size="sm" variant="ghost" onClick={() => view(d)} aria-label="file"><FileText size={14} /></Button>
                <Button size="sm" variant="ghost" onClick={() => remove(d)} aria-label={t("delete")}><Trash2 size={14} className="text-danger" /></Button>
              </td>
            </tr>))}</tbody>
        </table>
      </Card>

      {report && (
        <Card className="space-y-3" data-testid="report">
          <h2 className="text-lg font-bold">{t(`t_${report.doc.doc_type}` as Key)} · {report.doc.original_name}</h2>
          <Alert tone="warn">{t("ocrNotVerified")}</Alert>
          {report.doc.doc_type === "xray" && <Alert tone="info">{t("xrayNotice")}</Alert>}
          {Array.isArray(x.results) && (
            <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-muted"><tr>{(["test", "value", "unit", "range", "flag"] as Key[]).map((k) => <th key={k} className="p-2 text-start">{t(k)}</th>)}</tr></thead>
              <tbody>{x.results.map((r: any, i: number) => (
                <tr key={i} className="border-t border-border"><td className="p-2">{r.test}</td><td className="p-2 font-semibold" dir="ltr">{r.value}</td><td className="p-2" dir="ltr">{r.unit ?? "–"}</td>
                  <td className="p-2" dir="ltr">{r.reference_low != null ? `${r.reference_low} – ${r.reference_high}` : t("noRange")}</td>
                  <td className="p-2"><Badge tone={r.status === "high" || r.status === "low" ? "warn" : r.status === "within_range" ? "ok" : "info"}>{t(r.status as Key)}</Badge></td></tr>))}</tbody></table></div>
          )}
          {x.measurements && Object.keys(x.measurements).length > 0 && (
            <ul className="space-y-1 text-sm">{Object.entries(x.measurements).map(([k, v]: [string, any]) => <li key={k}><b dir="ltr">{k}: {v.value}</b> <span className="text-muted">— {v.meaning}</span></li>)}</ul>
          )}
          {Array.isArray(x.medications) && x.medications.length > 0 && <p className="text-sm">{x.medications.length} → <a className="text-brand underline" href="/app/medications">{t("nav_medications")}</a></p>}
          {x.image && <p className="text-sm" dir="ltr">{x.image.width}×{x.image.height} · {x.image.format} · {x.image.mode}</p>}
          {x.ocr_mean_confidence != null && <p className="text-xs text-muted">OCR confidence: {x.ocr_mean_confidence}/100 · {report.rep.ocr_engine}</p>}
          {report.rep.warnings.length > 0 && <div><h3 className="text-sm font-bold">{t("warnings")}</h3><ul className="list-disc ps-5 text-sm text-warn">{report.rep.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
          {x.disclaimer && <p className="text-xs text-muted">{x.disclaimer}</p>}
        </Card>
      )}
    </div>
  );
}
