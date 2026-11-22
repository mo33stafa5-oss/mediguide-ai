"use client";
import Link from "next/link";
import { Activity, FileHeart, MessageCircleHeart, Pill, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/logo";
import { HeroArt } from "@/components/hero-art";
import { LangToggle, ThemeToggle } from "@/components/toggles";
import { Button, Card } from "@/components/ui";
import { useI18n } from "@/lib/i18n/provider";

export default function Landing() {
  const { t } = useI18n();
  const features = [
    { i: MessageCircleHeart, h: t("featChat"), d: t("featChatD") },
    { i: Activity, h: t("featRisk"), d: t("featRiskD") },
    { i: FileHeart, h: t("featDocs"), d: t("featDocsD") },
    { i: Pill, h: t("featRx"), d: t("featRxD") },
    { i: ShieldCheck, h: t("featPrivacy"), d: t("featPrivacyD") },
  ];
  return (
    <main className="bg-hero min-h-dvh">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-4">
        <Logo />
        <nav className="flex items-center gap-1">
          <LangToggle /><ThemeToggle />
          <Button asChild variant="outline" size="sm"><Link href="/login">{t("signIn")}</Link></Button>
        </nav>
      </header>
      <section className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-10 md:grid-cols-2 md:py-16">
        <div className="space-y-5">
          <p className="inline-block rounded-full bg-soft px-3 py-1 text-sm font-semibold text-brand">{t("tagline")}</p>
          <h1 className="text-4xl font-extrabold leading-tight md:text-5xl"><span className="text-gradient">{t("heroTitle")}</span></h1>
          <p className="text-lg text-muted">{t("heroSub")}</p>
          <p className="font-semibold text-navy">{t("slogan")}</p>
          <div className="flex flex-wrap gap-3">
            <Button asChild><Link href="/register">{t("getStarted")}</Link></Button>
            <Button asChild variant="outline"><Link href="/login">{t("signIn")}</Link></Button>
          </div>
        </div>
        <HeroArt />
      </section>
      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-12 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ i: Icon, h, d }) => (
          <Card key={h} className="space-y-2 transition hover:-translate-y-1 hover:shadow-lg">
            <span className="gradient-brand inline-flex h-11 w-11 items-center justify-center rounded-2xl text-white"><Icon size={22} /></span>
            <h2 className="text-lg font-bold">{h}</h2>
            <p className="text-sm text-muted">{d}</p>
          </Card>
        ))}
      </section>
      <footer className="border-t border-border px-4 py-6 text-center text-sm text-muted">{t("disclaimerFull")}</footer>
    </main>
  );
}
