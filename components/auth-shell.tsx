"use client";
import Link from "next/link";
import { Logo } from "@/components/logo";
import { LangToggle, ThemeToggle } from "@/components/toggles";
import { Card } from "@/components/ui";
import { useI18n } from "@/lib/i18n/provider";

export function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <main className="bg-hero flex min-h-dvh flex-col items-center px-4 py-6">
      <div className="flex w-full max-w-md items-center justify-between">
        <Link href="/"><Logo size={30} /></Link>
        <div className="flex"><LangToggle /><ThemeToggle /></div>
      </div>
      <Card className="mt-8 w-full max-w-md space-y-5 p-6">
        <h1 className="text-2xl font-extrabold">{title}</h1>
        {children}
      </Card>
      <p className="mt-6 max-w-md text-center text-xs text-muted">{t("disclaimerShort")}</p>
    </main>
  );
}
