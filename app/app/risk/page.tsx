"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Alert, Badge, Button, Card, Field, Input, Select, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import type { Key } from "@/lib/i18n/dict";

const num = (min: number, max: number) => z.coerce.number().min(min).max(max);
const schema = z.object({
  age: num(18, 100).int(), sex: z.coerce.number().pipe(z.union([z.literal(0), z.literal(1)])), cp: z.coerce.number().int().min(1).max(4),
  trestbps: num(70, 250).int(), chol: num(80, 700).int(), fbs: z.coerce.number().pipe(z.union([z.literal(0), z.literal(1)])), restecg: z.coerce.number().int().min(0).max(2),
  thalach: num(60, 230).int(), exang: z.coerce.number().pipe(z.union([z.literal(0), z.literal(1)])), oldpeak: num(0, 7), slope: z.coerce.number().int().min(1).max(3),
  ca: num(0, 3).int(), thal: z.coerce.number().pipe(z.union([z.literal(3), z.literal(6), z.literal(7)])),
});
type Form = z.input<typeof schema>;
type Result = { score: number; prediction: number; model_version: string; model_name: string; label: string; test_metrics_of_selected_model: Record<string, number>;
  limitations: Record<string, string[]>; recommendations: Record<string, string[]>; disclaimer: Record<string, string>; explanation: Record<string, string> };
type Past = { id: string; score: number; created_at: string; model_version: string };

export default function RiskPage() {
  const { t, locale } = useI18n();
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState("");
  const [past, setPast] = useState<Past[]>([]);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) as never, defaultValues: { sex: 1, cp: 1, fbs: 0, restecg: 0, exang: 0, slope: 1, thal: 3, ca: 0, oldpeak: 0 } });
  const load = () => createClient().from("heart_risk_assessments").select("id,score,created_at,model_version").order("created_at", { ascending: false }).limit(10).then(({ data }) => setPast((data as Past[]) ?? []));
  useEffect(() => { load(); }, []);
  const onSubmit = handleSubmit(async (v) => {
    setErr("");
    try { setRes(await api<Result>("/api/predict", { method: "POST", json: schema.parse(v) })); load(); }
    catch (e) { setErr(e instanceof ApiError ? e.message : t("errorGeneric")); }
  });
  const E = (k: keyof Form) => (errors[k] ? "!" : undefined);
  const opts = (prefix: string, vals: number[]) => vals.map((v) => <option key={v} value={v}>{t(`${prefix}${v}` as Key)}</option>);
  const yn = <><option value={0}>{t("no")}</option><option value={1}>{t("yes")}</option></>;
  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-extrabold">{t("riskTitle")}</h1><p className="text-sm text-muted">{t("riskIntro")}</p></div>
      <Alert tone="warn">{t("disclaimerFull")}</Alert>
      <form onSubmit={onSubmit} noValidate className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label={t("f_age")} error={E("age")}><Input type="number" {...register("age")} /></Field>
        <Field label={t("f_sex")}><Select {...register("sex")}><option value={1}>{t("male")}</option><option value={0}>{t("female")}</option></Select></Field>
        <Field label={t("f_cp")}><Select {...register("cp")}>{opts("cp", [1, 2, 3, 4])}</Select></Field>
        <Field label={t("f_trestbps")} error={E("trestbps")}><Input type="number" {...register("trestbps")} /></Field>
        <Field label={t("f_chol")} error={E("chol")}><Input type="number" {...register("chol")} /></Field>
        <Field label={t("f_fbs")}><Select {...register("fbs")}>{yn}</Select></Field>
        <Field label={t("f_restecg")}><Select {...register("restecg")}>{opts("ecg", [0, 1, 2])}</Select></Field>
        <Field label={t("f_thalach")} error={E("thalach")}><Input type="number" {...register("thalach")} /></Field>
        <Field label={t("f_exang")}><Select {...register("exang")}>{yn}</Select></Field>
        <Field label={t("f_oldpeak")} error={E("oldpeak")}><Input type="number" step="0.1" {...register("oldpeak")} /></Field>
        <Field label={t("f_slope")}><Select {...register("slope")}>{opts("slope", [1, 2, 3])}</Select></Field>
        <Field label={t("f_ca")} error={E("ca")}><Input type="number" {...register("ca")} /></Field>
        <Field label={t("f_thal")}><Select {...register("thal")}>{opts("thal", [3, 6, 7])}</Select></Field>
        <div className="flex items-end"><Button type="submit" className="w-full" disabled={isSubmitting} data-testid="risk-submit">{isSubmitting && <Spinner />}{t("calculate")}</Button></div>
      </form>
      {Object.keys(errors).length > 0 && <Alert tone="danger">{Object.keys(errors).join(", ")}</Alert>}
      {err && <Alert tone="danger">{err}</Alert>}
      {res && (
        <Card className="space-y-4" data-testid="risk-result">
          <div className="flex flex-wrap items-center gap-3">
            <div className="gradient-brand rounded-2xl px-5 py-3 text-white"><p className="text-xs opacity-80">{t("modelScore")}</p><p className="text-3xl font-extrabold">{Math.round(res.score * 100)}%</p></div>
            <div className="space-y-1"><Badge tone={res.prediction ? "warn" : "ok"}>{res.prediction ? t("higherPattern") : t("lowerPattern")}</Badge>
              <p className="text-xs text-muted">{t("modelVersion")}: {res.model_version} · {res.model_name}</p></div>
          </div>
          <p className="text-sm">{res.explanation[locale]}</p>
          <div>
            <h2 className="mb-1 text-sm font-bold">{t("modelMetrics")}</h2>
            <div className="h-40"><ResponsiveContainer><BarChart data={Object.entries(res.test_metrics_of_selected_model).map(([k, v]) => ({ k, v }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="k" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 11 }} /><Tooltip />
              <Bar dataKey="v" radius={6}>{Object.keys(res.test_metrics_of_selected_model).map((k) => <Cell key={k} fill="#1677e8" />)}</Bar></BarChart></ResponsiveContainer></div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div><h2 className="mb-1 text-sm font-bold">{t("limitations")}</h2><ul className="list-disc ps-5 text-sm text-muted">{res.limitations[locale].map((x) => <li key={x}>{x}</li>)}</ul></div>
            <div><h2 className="mb-1 text-sm font-bold">{t("recommendations")}</h2><ul className="list-disc ps-5 text-sm text-muted">{res.recommendations[locale].map((x) => <li key={x}>{x}</li>)}</ul></div>
          </div>
          <Alert tone="warn">{res.disclaimer[locale]}</Alert>
        </Card>
      )}
      {past.length > 0 && (
        <Card><h2 className="mb-2 font-bold">{t("pastAssessments")}</h2>
          <ul className="divide-y divide-border text-sm">{past.map((p) => <li key={p.id} className="flex justify-between py-2"><span>{new Date(p.created_at).toLocaleString(locale === "ar" ? "ar-EG" : "en-GB")}</span><span>{Math.round(p.score * 100)}% · <span className="text-muted">{p.model_version}</span></span></li>)}</ul>
          <p className="mt-2 text-xs text-muted">Scores are only comparable when produced by the same model version.</p></Card>
      )}
    </div>
  );
}
