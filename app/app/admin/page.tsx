"use client";
import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useMe } from "@/components/app-shell";
import { Alert, Badge, Button, Card, Field, Input, Select, Textarea } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import type { Key } from "@/lib/i18n/dict";

type Tab = "system" | "users" | "knowledge" | "evaluation" | "audit";
type U = { id: string; full_name: string; role: string; status: string; created_at: string };
type K = { id: string; source_name: string; source_url: string; title: string; status: string; last_reviewed_on: string | null; content: string };

export default function AdminPage() {
  const { t } = useI18n();
  const me = useMe();
  const [tab, setTab] = useState<Tab>(me.role === "admin" ? "system" : "knowledge");
  if (me.role === "patient") return <Alert tone="danger">{t("forbidden")}</Alert>;
  const tabs: Tab[] = me.role === "admin" ? ["system", "users", "knowledge", "evaluation", "audit"] : ["knowledge"];
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-extrabold">{t("adminTitle")}</h1>
      <Alert tone="info">{t("adminNote")}</Alert>
      <div className="flex flex-wrap gap-2" role="tablist">
        {tabs.map((k) => <Button key={k} role="tab" aria-selected={tab === k} variant={tab === k ? "default" : "outline"} size="sm" onClick={() => setTab(k)} data-testid={`tab-${k}`}>{t(k === "audit" ? "audit" : (k as Key))}</Button>)}
      </div>
      {tab === "system" && <System />}{tab === "users" && <Users meId={me.id} />}{tab === "knowledge" && <Knowledge />}{tab === "evaluation" && <Evaluation />}{tab === "audit" && <Audit />}
    </div>
  );
}

function System() {
  const [o, setO] = useState<Record<string, any> | null>(null);
  const [h, setH] = useState<Record<string, any> | null>(null);
  useEffect(() => { api<Record<string, any>>("/api/admin/overview").then(setO).catch(() => {}); fetch("/api/health").then((r) => r.json()).then(setH).catch(() => {}); }, []);
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card><h2 className="mb-2 font-bold">API health</h2>{h ? <ul className="space-y-1 text-sm">{Object.entries(h.services).map(([k, v]: [string, any]) => <li key={k} className="flex justify-between"><b>{k}</b><span className="text-muted" dir="ltr">{JSON.stringify(v)}</span></li>)}</ul> : "…"}</Card>
      <Card><h2 className="mb-2 font-bold">Storage & data</h2>{o ? <ul className="space-y-1 text-sm">
        {(["users", "documents", "conversations", "knowledge_pending", "knowledge_approved"] as const).map((k) => <li key={k} className="flex justify-between"><span>{k}</span><b>{o[k]}</b></li>)}
        <li className="flex justify-between"><span>buckets</span><span dir="ltr" className="text-xs">{o.storage_buckets?.join(", ")}</span></li>
        <li className="flex justify-between"><span>model</span><span dir="ltr" className="text-xs">{o.model?.model_version}</span></li></ul> : "…"}</Card>
    </div>
  );
}

function Users({ meId }: { meId: string }) {
  const { t } = useI18n();
  const [us, setUs] = useState<U[]>([]);
  const [err, setErr] = useState("");
  const load = useCallback(() => api<{ users: U[] }>("/api/admin/users").then((r) => setUs(r.users)), []);
  useEffect(() => { load(); }, [load]);
  const patch = async (id: string, body: object) => { setErr(""); try { await api(`/api/admin/users/${id}`, { method: "PATCH", json: body }); load(); } catch (e) { setErr(e instanceof ApiError ? e.message : ""); } };
  return (
    <Card className="overflow-x-auto p-0">{err && <Alert tone="danger" className="m-3">{err}</Alert>}
      <table className="w-full text-sm"><thead className="bg-soft text-xs text-muted"><tr><th className="p-3 text-start">{t("fullName")}</th><th className="p-3 text-start">{t("role")}</th><th className="p-3 text-start">{t("status")}</th><th /></tr></thead>
        <tbody>{us.map((u) => (
          <tr key={u.id} className="border-t border-border"><td className="p-3">{u.full_name || u.id.slice(0, 8)}</td>
            <td className="p-3"><Select value={u.role} disabled={u.id === meId} onChange={(e) => patch(u.id, { role: e.target.value })} className="h-9"><option value="patient">patient</option><option value="medical_reviewer">medical_reviewer</option><option value="admin">admin</option></Select></td>
            <td className="p-3"><Badge tone={u.status === "active" ? "ok" : "danger"}>{u.status}</Badge></td>
            <td className="p-3 text-end">{u.id !== meId && <Button size="sm" variant="outline" onClick={() => patch(u.id, { status: u.status === "active" ? "suspended" : "active" })}>{u.status === "active" ? t("suspend") : t("activate")}</Button>}</td></tr>))}</tbody></table></Card>
  );
}

function Knowledge() {
  const { t } = useI18n();
  const sb = createClient();
  const [rows, setRows] = useState<K[]>([]);
  const [f, setF] = useState({ source_name: "", source_url: "", title: "", text: "", language: "en", last_reviewed_on: "", published_on: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const load = useCallback(async () => { const { data } = await sb.from("medical_knowledge").select("id,source_name,source_url,title,status,last_reviewed_on,content").order("created_at", { ascending: false }).limit(100); setRows(data ?? []); }, [sb]);
  useEffect(() => { load(); }, [load]);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));
  async function ingest() {
    setMsg(null);
    try { const r = await api<{ chunks_created: number }>("/api/knowledge/ingest", { method: "POST", json: { ...f, last_reviewed_on: f.last_reviewed_on || null, published_on: f.published_on || null } }); setMsg({ ok: true, text: `${r.chunks_created} chunks (pending)` }); load(); }
    catch (e) { setMsg({ ok: false, text: e instanceof ApiError ? (e.fields ? e.fields.map((x) => x.field).join(", ") : e.message) : t("errorGeneric") }); }
  }
  const status = async (id: string, s: string) => { await api(`/api/knowledge/${id}/status`, { method: "POST", json: { status: s } }); load(); };
  return (
    <div className="space-y-4">
      <Card className="grid gap-3 sm:grid-cols-2"><h2 className="font-bold sm:col-span-2">{t("addKnowledge")}</h2>
        <Field label={t("sourceName")}><Input value={f.source_name} onChange={set("source_name")} placeholder="MedlinePlus" /></Field>
        <Field label={t("sourceUrl")}><Input value={f.source_url} onChange={set("source_url")} dir="ltr" placeholder="https://" /></Field>
        <Field label={t("title")}><Input value={f.title} onChange={set("title")} /></Field>
        <Field label={t("lang")}><Select value={f.language} onChange={set("language")}><option value="en">English</option><option value="ar">العربية</option></Select></Field>
        <Field label={t("lastReviewed")}><Input value={f.last_reviewed_on} onChange={set("last_reviewed_on")} dir="ltr" /></Field>
        <Field label={t("published") + " (YYYY-MM-DD)"}><Input value={f.published_on} onChange={set("published_on")} dir="ltr" /></Field>
        <div className="sm:col-span-2"><Field label={t("text")}><Textarea value={f.text} onChange={set("text")} className="min-h-40" /></Field></div>
        <div className="flex items-center gap-3 sm:col-span-2"><Button onClick={ingest}>{t("ingest")}</Button>{msg && <Alert tone={msg.ok ? "ok" : "danger"}>{msg.text}</Alert>}</div>
      </Card>
      <Card className="overflow-x-auto p-0"><table className="w-full text-sm"><tbody>{rows.map((r) => (
        <tr key={r.id} className="border-t border-border first:border-0 align-top"><td className="p-3"><p className="font-semibold">{r.source_name} — {r.title}</p><p className="line-clamp-2 text-xs text-muted">{r.content}</p></td>
          <td className="p-3"><Badge tone={r.status === "approved" ? "ok" : r.status === "pending" ? "warn" : "danger"}>{r.status}</Badge></td>
          <td className="flex gap-1 p-3"><Button size="sm" variant="outline" onClick={() => status(r.id, "approved")}>{t("approve")}</Button><Button size="sm" variant="ghost" onClick={() => status(r.id, "rejected")}>{t("reject")}</Button></td></tr>))}</tbody></table></Card>
    </div>
  );
}

function Evaluation() {
  const [m, setM] = useState<any>(null);
  useEffect(() => { api("/api/admin/evaluation").then(setM).catch(() => {}); }, []);
  if (!m) return <p>…</p>;
  const data = Object.entries(m.results).map(([k, v]: [string, any]) => ({ model: k, ...v.test }));
  return (
    <Card className="space-y-3"><p className="text-sm">Model <b dir="ltr">{m.model_version}</b> — selected: <b>{m.selected_model}</b> ({m.selection_rule}). Rows {m.dataset.rows} (train {m.dataset.train_rows} / test {m.dataset.test_rows}). Trained {m.trained_at_utc}.</p>
      <div className="h-72"><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="model" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} /><Tooltip /><Legend />
        <Bar dataKey="accuracy" fill="#1677e8" /><Bar dataKey="recall" fill="#16c5d5" /><Bar dataKey="f1" fill="#102a56" /><Bar dataKey="roc_auc" fill="#0f9d6b" /></BarChart></ResponsiveContainer></div>
      <p className="text-xs text-muted">{m.disclaimer}</p></Card>
  );
}

function Audit() {
  const [l, setL] = useState<{ id: number; actor_id: string | null; action: string; entity: string | null; created_at: string }[]>([]);
  useEffect(() => { api<{ logs: typeof l }>("/api/admin/audit-logs").then((r) => setL(r.logs)).catch(() => {}); }, []);
  return <Card className="overflow-x-auto p-0"><table className="w-full text-xs" dir="ltr"><tbody>{l.map((x) => <tr key={x.id} className="border-t border-border first:border-0"><td className="p-2 text-muted">{new Date(x.created_at).toISOString().slice(0, 19)}</td><td className="p-2 font-semibold">{x.action}</td><td className="p-2">{x.entity}</td><td className="p-2 text-muted">{x.actor_id?.slice(0, 8)}</td></tr>)}</tbody></table></Card>;
}
