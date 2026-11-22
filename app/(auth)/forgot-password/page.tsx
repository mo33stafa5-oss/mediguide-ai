"use client";
import { useState } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field, Input } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

export default function Page() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <AuthShell title={t("forgotPassword")}>
      <form className="space-y-4" onSubmit={async (e) => {
        e.preventDefault();
        await createClient().auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/auth/callback?next=/reset-password` });
        setSent(true); // same message whether or not the email exists (no account enumeration)
      }}>
        <Field label={t("email")}><Input type="email" required dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        {sent && <Alert tone="ok">{t("resetSent")}</Alert>}
        <Button type="submit" className="w-full">{t("sendReset")}</Button>
      </form>
    </AuthShell>
  );
}
