"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field, Input } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

export default function Page() {
  const { t } = useI18n();
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  return (
    <AuthShell title={t("newPassword")}>
      <form className="space-y-4" onSubmit={async (e) => {
        e.preventDefault();
        const { error } = await createClient().auth.updateUser({ password: pw });
        if (error) return setMsg({ ok: false, text: error.message });
        setMsg({ ok: true, text: t("passwordUpdated") });
        setTimeout(() => router.replace("/app"), 800);
      }}>
        <Field label={t("newPassword")} hint={t("passwordHint")}><Input type="password" minLength={8} required dir="ltr" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        {msg && <Alert tone={msg.ok ? "ok" : "danger"}>{msg.text}</Alert>}
        <Button type="submit" className="w-full">{t("updatePassword")}</Button>
      </form>
    </AuthShell>
  );
}
