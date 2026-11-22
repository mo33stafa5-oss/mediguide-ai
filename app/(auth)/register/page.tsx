"use client";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field, Input, Spinner } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

const schema = z.object({
  fullName: z.string().min(2).max(100),
  email: z.string().email(),
  password: z.string().min(8).regex(/[A-Za-z]/).regex(/\d/),
  consent: z.literal(true, { error: "required" }),
});

export default function Page() {
  const { t, locale } = useI18n();
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  const onSubmit = handleSubmit(async (v) => {
    setErr("");
    const { error } = await createClient().auth.signUp({
      email: v.email, password: v.password,
      options: { emailRedirectTo: `${location.origin}/auth/callback`, data: { full_name: v.fullName, locale, consent_terms: "true" } },
    });
    if (error) return setErr(error.message);
    setDone(true);
  });
  return (
    <AuthShell title={t("signUp")}>
      {done ? <Alert tone="ok" data-testid="check-email">{t("checkEmail")}</Alert> : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field label={t("fullName")} error={errors.fullName?.message}><Input autoComplete="name" {...register("fullName")} /></Field>
          <Field label={t("email")} error={errors.email?.message}><Input type="email" autoComplete="email" dir="ltr" {...register("email")} /></Field>
          <Field label={t("password")} hint={t("passwordHint")} error={errors.password ? t("passwordHint") : undefined}><Input type="password" autoComplete="new-password" dir="ltr" {...register("password")} /></Field>
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" {...register("consent")} /><span>{t("consentTerms")}</span></label>
          {errors.consent && <p role="alert" className="text-xs text-danger">{t("consentTerms")}</p>}
          {err && <Alert tone="danger">{err}</Alert>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting && <Spinner />}{t("signUp")}</Button>
        </form>
      )}
      <p className="text-sm">{t("haveAccount")} <Link href="/login" className="text-brand hover:underline">{t("signIn")}</Link></p>
    </AuthShell>
  );
}
