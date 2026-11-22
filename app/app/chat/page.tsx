"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, MessageSquarePlus, Send, Trash2, TriangleAlert, ExternalLink } from "lucide-react";
import { useMe } from "@/components/app-shell";
import { Alert, Button, Card, Spinner } from "@/components/ui";
import { authHeaders } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type Source = { n: number; source_name: string; source_url: string; title: string; published_on?: string; last_reviewed_on?: string; excerpt: string };
type Msg = { id: string; role: "user" | "assistant"; content: string; created_at: string; sources?: Source[]; is_emergency?: boolean };
type Conv = { id: string; title: string; updated_at: string };

export default function ChatPage() {
  const { t, locale } = useI18n();
  const me = useMe();
  const sb = createClient();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [consent, setConsent] = useState(me.consent_ai);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const loadConvs = useCallback(async () => {
    const { data } = await sb.from("conversations").select("id,title,updated_at").order("updated_at", { ascending: false });
    setConvs(data ?? []);
  }, [sb]);
  useEffect(() => { loadConvs(); }, [loadConvs]);
  useEffect(() => { fetch(`/api/chat/suggestions?locale=${locale}`).then((r) => r.json()).then((j) => setSuggestions(j.suggestions ?? [])).catch(() => {}); }, [locale]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function open(id: string | null) {
    setActive(id); setErr("");
    if (!id) return setMsgs([]);
    const { data } = await sb.from("messages").select("id,role,content,created_at,sources,is_emergency").eq("conversation_id", id).order("created_at");
    setMsgs((data as Msg[]) ?? []);
  }

  async function giveConsent() {
    const { error } = await sb.from("profiles").update({ consent_ai_processing_at: new Date().toISOString() }).eq("id", me.id);
    if (!error) setConsent(true);
  }

  async function send(text: string) {
    text = text.trim();
    if (!text || busy) return;
    setBusy(true); setErr(""); setInput("");
    const now = new Date().toISOString();
    const aId = `tmp-${Date.now()}`;
    setMsgs((m) => [...m, { id: `u-${Date.now()}`, role: "user", content: text, created_at: now }, { id: aId, role: "assistant", content: "", created_at: now }]);
    try {
      const res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json", ...(await authHeaders()) },
        body: JSON.stringify({ message: text, conversation_id: active, locale }),
      });
      if (!res.ok || !res.body) {
        const j = await res.json().catch(() => ({}));
        setMsgs((m) => m.filter((x) => x.id !== aId));
        setErr(j?.error?.code === "service_not_configured" ? t("notConfigured") : j?.error?.message ?? t("errorGeneric"));
        return;
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      const patch = (fn: (x: Msg) => Msg) => setMsgs((m) => m.map((x) => (x.id === aId ? fn(x) : x)));
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const p of parts) {
          if (!p.startsWith("data: ")) continue;
          const ev = JSON.parse(p.slice(6));
          if (ev.type === "meta") { if (!active) setActive(ev.conversation_id); if (ev.emergency) patch((x) => ({ ...x, is_emergency: true })); }
          else if (ev.type === "delta") patch((x) => ({ ...x, content: x.content + ev.text }));
          else if (ev.type === "sources") patch((x) => ({ ...x, sources: ev.sources }));
          else if (ev.type === "error") setErr(ev.code === "service_not_configured" ? t("notConfigured") : ev.message);
          else if (ev.type === "done") patch((x) => ({ ...x, id: ev.message_id }));
        }
      }
      loadConvs();
    } catch { setErr(t("errorGeneric")); } finally { setBusy(false); }
  }

  async function remove(id: string) {
    await sb.from("conversations").delete().eq("id", id);
    if (active === id) open(null);
    loadConvs();
  }
  const copy = async (m: Msg) => { await navigator.clipboard.writeText(m.content); setCopied(m.id); setTimeout(() => setCopied(null), 1500); };
  const time = (s: string) => new Date(s).toLocaleTimeString(locale === "ar" ? "ar-EG" : "en-GB", { hour: "2-digit", minute: "2-digit" });

  if (!consent) {
    return (
      <Card className="mx-auto max-w-lg space-y-3">
        <h1 className="text-xl font-bold">{t("consentTitle")}</h1>
        <p className="text-sm">{t("consentBody")}</p>
        <Button onClick={giveConsent} data-testid="consent-btn">{t("consentBtn")}</Button>
      </Card>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
      <Card className="h-fit space-y-2 p-3">
        <Button variant="outline" size="sm" className="w-full" onClick={() => open(null)} data-testid="new-chat"><MessageSquarePlus size={16} />{t("newChat")}</Button>
        <p className="px-1 pt-1 text-xs font-semibold text-muted">{t("history")}</p>
        <ul className="max-h-64 space-y-1 overflow-auto">
          {convs.map((c) => (
            <li key={c.id} className={cn("group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm hover:bg-soft", active === c.id && "bg-soft font-semibold")}>
              <button className="min-w-0 flex-1 truncate text-start" onClick={() => open(c.id)}>{c.title}</button>
              <button aria-label={t("delete")} onClick={() => remove(c.id)} className="text-muted hover:text-danger"><Trash2 size={14} /></button>
            </li>
          ))}
        </ul>
      </Card>
      <Card className="flex min-h-[60dvh] flex-col p-0">
        <div className="flex-1 space-y-4 overflow-auto p-4" aria-live="polite">
          {msgs.length === 0 && (
            <div className="space-y-3 py-6 text-center">
              <h1 className="text-xl font-bold">{t("nav_chat")}</h1>
              <p className="text-sm text-muted">{t("suggested")}</p>
              <div className="flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-border bg-soft px-3 py-1.5 text-sm hover:border-brand">{s}</button>)}
              </div>
            </div>
          )}
          {msgs.map((m) => (
            <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div className={cn("max-w-[92%] rounded-2xl px-4 py-3 text-sm", m.role === "user" ? "gradient-brand text-white" : "border border-border bg-background")} data-testid={`msg-${m.role}`}>
                {m.is_emergency && m.role === "assistant" && <Alert tone="danger" className="mb-2 flex items-center gap-2 font-bold"><TriangleAlert size={16} />{t("emergencyBanner")}</Alert>}
                {m.role === "assistant" ? (
                  m.content ? <div className="prose-chat"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div> : <span className="flex items-center gap-2 text-muted"><Spinner />{t("thinking")}</span>
                ) : <p className="whitespace-pre-wrap">{m.content}</p>}
                {m.sources && m.sources.length > 0 && (
                  <details className="mt-2 rounded-lg bg-soft p-2 text-xs" open>
                    <summary className="cursor-pointer font-semibold">{t("sources")} ({m.sources.length})</summary>
                    <ul className="mt-1 space-y-1.5">
                      {m.sources.map((s) => (
                        <li key={s.n}><a href={s.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-brand hover:underline">[{s.n}] {s.source_name} — {s.title}<ExternalLink size={11} /></a>
                          <div className="text-muted">{s.last_reviewed_on && <>{t("reviewed")}: {s.last_reviewed_on} · </>}{s.published_on && <>{t("published")}: {s.published_on}</>}</div></li>
                      ))}
                    </ul>
                  </details>
                )}
                <div className={cn("mt-1.5 flex items-center gap-2 text-[11px]", m.role === "user" ? "text-white/80" : "text-muted")}>
                  <time>{time(m.created_at)}</time>
                  {m.role === "assistant" && m.content && <button onClick={() => copy(m)} className="inline-flex items-center gap-1 hover:text-brand" aria-label={t("copy")}>{copied === m.id ? <Check size={12} /> : <Copy size={12} />}{copied === m.id ? t("copied") : t("copy")}</button>}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottom} />
        </div>
        {err && <Alert tone="danger" className="mx-4 mb-2">{err} <button className="underline" onClick={() => setErr("")}>×</button></Alert>}
        <form className="flex gap-2 border-t border-border p-3" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} maxLength={4000} placeholder={t("typeMessage")} data-testid="chat-input"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            className="max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-border bg-card px-3 py-2.5 text-sm focus:border-brand focus:outline-none" />
          <Button type="submit" disabled={busy || !input.trim()} aria-label={t("send")} data-testid="chat-send">{busy ? <Spinner /> : <Send size={18} className="rtl:-scale-x-100" />}</Button>
        </form>
        <p className="px-4 pb-3 text-[11px] text-muted">{t("disclaimerShort")}</p>
      </Card>
    </div>
  );
}
