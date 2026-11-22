"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Field, Input, Spinner } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";

const schema = z.object({ email: z.string().email(), password: z.string().min(8) });

function LoginForm() {
  const { t } = useI18n();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [err, setErr] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  const onSubmit = handleSubmit(async (v) => {
    setErr("");
    const { error } = await createClient().auth.signInWithPassword(v);
    if (error) return setErr(error.message);
    router.replace(next && next.startsWith("/app") ? next : "/app");
    router.refresh();
  });
  return (
    <AuthShell title={t("signIn")}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label={t("email")} error={errors.email?.message}><Input type="email" autoComplete="email" dir="ltr" {...register("email")} /></Field>
        <Field label={t("password")} error={errors.password?.message}><Input type="password" autoComplete="current-password" dir="ltr" {...register("password")} /></Field>
        {err && <Alert tone="danger">{err}</Alert>}
        <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting && <Spinner />}{t("signIn")}</Button>
      </form>
      <div className="flex justify-between text-sm">
        <Link href="/forgot-password" className="text-brand hover:underline">{t("forgotPassword")}</Link>
        <Link href="/register" className="text-brand hover:underline">{t("noAccount")} {t("signUp")}</Link>
      </div>
    </AuthShell>
  );
}
export default function Page() { return <Suspense><LoginForm /></Suspense>; }
