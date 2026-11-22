"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, FileHeart, MessageCircleHeart, Pill } from "lucide-react";
import { useMe } from "@/components/app-shell";
import { Alert, Badge, Card } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import type { Key } from "@/lib/i18n/dict";

type Event = { at: string; kind: "chat" | "risk" | "doc"; label: string; href: string };

export default function Dashboard() {
  const { t, locale } = useI18n();
  const me = useMe();
  const [d, setD] = useState<{ docs: number; chats: number; assess: number; meds: number; events: Event[] } | null>(null);
  useEffect(() => {
    const sb = createClient();
    (async () => {
      const [docs, chats, ass, meds] = await Promise.all([
        sb.from("medical_documents").select("id,doc_type,status,created_at", { count: "exact" }).order("created_at", { ascending: false }).limit(5),
        sb.from("conversations").select("id,title,updated_at", { count: "exact" }).order("updated_at", { ascending: false }).limit(5),
        sb.from("heart_risk_assessments").select("id,score,created_at", { count: "exact" }).order("created_at", { ascending: false }).limit(5),
        sb.from("medication_records").select("id", { count: "exact", head: true }).eq("active", true),
      ]);
      const events: Event[] = [
        ...(docs.data ?? []).map((x) => ({ at: x.created_at, kind: "doc" as const, label: t(`t_${x.doc_type}` as Key), href: "/app/documents" })),
        ...(chats.data ?? []).map((x) => ({ at: x.updated_at, kind: "chat" as const, label: x.title, href: "/app/chat" })),
        ...(ass.data ?? []).map((x) => ({ at: x.created_at, kind: "risk" as const, label: `${t("modelScore")}: ${Math.round(x.score * 100)}%`, href: "/app/risk" })),
      ].sort((a, b) => +new Date(b.at) - +new Date(a.at)).slice(0, 8);
      setD({ docs: docs.count ?? 0, chats: chats.count ?? 0, assess: ass.count ?? 0, meds: meds.count ?? 0, events });
    })();
  }, [t]);
  const stats = [
    { k: "statDocs" as Key, v: d?.docs, i: FileHeart, href: "/app/documents" }, { k: "statChats" as Key, v: d?.chats, i: MessageCircleHeart, href: "/app/chat" },
    { k: "statAssess" as Key, v: d?.assess, i: Activity, href: "/app/risk" }, { k: "statMeds" as Key, v: d?.meds, i: Pill, href: "/app/medications" },
  ];
  const fmt = (s: string) => new Date(s).toLocaleString(locale === "ar" ? "ar-EG" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  return (
    <div className="space-y-6">
      <div className="gradient-brand rounded-card p-6 text-white">
        <h1 className="text-2xl font-extrabold">{t("welcome")}{me.full_name ? `، ${me.full_name}` : ""}</h1>
        <p className="opacity-90">{t("dashboardIntro")}</p>
      </div>
      <Alert tone="warn">{t("disclaimerFull")}</Alert>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map(({ k, v, i: Icon, href }) => (
          <Link key={k} href={href}><Card className="flex items-center gap-3 transition hover:-translate-y-0.5">
            <span className="rounded-xl bg-soft p-2 text-brand"><Icon size={20} /></span>
            <div><p className="text-2xl font-extrabold" data-testid={`stat-${k}`}>{v ?? "–"}</p><p className="text-xs text-muted">{t(k)}</p></div>
          </Card></Link>
        ))}
      </div>
      <Card>
        <h2 className="mb-3 text-lg font-bold">{t("timeline")}</h2>
        {d && d.events.length === 0 && <p className="text-sm text-muted">{t("noTimeline")}</p>}
        <ol className="space-y-3 border-s-2 border-border ps-4">
          {d?.events.map((e, i) => (
            <li key={i} className="relative">
              <span className="absolute -start-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full bg-brand" />
              <Link href={e.href} className="flex flex-wrap items-center gap-2 hover:underline">
                <Badge>{e.kind}</Badge><span className="text-sm font-medium">{e.label}</span><span className="text-xs text-muted">{fmt(e.at)}</span>
              </Link>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
