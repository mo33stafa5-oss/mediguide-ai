"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext } from "react";
import { Activity, FileHeart, Home, LogOut, MessageCircleHeart, Pill, Settings2, ShieldCheck, UserCog } from "lucide-react";
import { Logo } from "@/components/logo";
import { LangToggle, ThemeToggle } from "@/components/toggles";
import { Button } from "@/components/ui";
import { createClient } from "@/lib/supabase/client";
import { useI18n } from "@/lib/i18n/provider";
import type { Key } from "@/lib/i18n/dict";
import { cn } from "@/lib/utils";

export type Me = { id: string; email: string; full_name: string; role: "patient" | "admin" | "medical_reviewer"; consent_ai: boolean };
const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx)!;

const NAV: { href: string; k: Key; icon: typeof Home; roles?: Me["role"][] }[] = [
  { href: "/app", k: "nav_dashboard", icon: Home },
  { href: "/app/chat", k: "nav_chat", icon: MessageCircleHeart },
  { href: "/app/risk", k: "nav_risk", icon: Activity },
  { href: "/app/documents", k: "nav_documents", icon: FileHeart },
  { href: "/app/medications", k: "nav_medications", icon: Pill },
  { href: "/app/profile", k: "nav_profile", icon: UserCog },
  { href: "/app/admin", k: "nav_admin", icon: Settings2, roles: ["admin", "medical_reviewer"] },
];

export function AppShell({ me, children }: { me: Me; children: React.ReactNode }) {
  const { t } = useI18n();
  const path = usePathname();
  const router = useRouter();
  const items = NAV.filter((n) => !n.roles || n.roles.includes(me.role));
  const active = (h: string) => (h === "/app" ? path === h : path.startsWith(h));
  return (
    <MeCtx.Provider value={me}>
      <div className="min-h-dvh md:flex">
        <aside className="hidden w-64 shrink-0 border-e border-border bg-card p-4 md:flex md:flex-col">
          <Link href="/app" className="mb-6 block"><Logo size={32} /></Link>
          <nav className="flex-1 space-y-1" aria-label="Main">
            {items.map(({ href, k, icon: Icon }) => (
              <Link key={href} href={href} aria-current={active(href) ? "page" : undefined}
                className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition hover:bg-soft", active(href) && "gradient-brand text-white hover:brightness-110")}>
                <Icon size={18} />{t(k)}
              </Link>
            ))}
          </nav>
          <div className="mt-4 space-y-2 border-t border-border pt-4">
            <p className="truncate text-sm font-semibold">{me.full_name || me.email}</p>
            <p className="flex items-center gap-1 text-xs text-muted"><ShieldCheck size={12} />{me.role}</p>
            <div className="flex items-center"><LangToggle /><ThemeToggle /></div>
            <Button variant="outline" size="sm" className="w-full" onClick={async () => { await createClient().auth.signOut(); router.replace("/"); router.refresh(); }}>
              <LogOut size={16} />{t("signOut")}
            </Button>
          </div>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col pb-20 md:pb-0">
          <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3 md:hidden">
            <Logo size={28} />
            <div className="flex"><LangToggle /><ThemeToggle /></div>
          </header>
          <main className="mx-auto w-full max-w-5xl flex-1 p-4 md:p-8">{children}</main>
          <footer className="border-t border-border px-4 py-3 text-center text-xs text-muted">{t("disclaimerShort")}</footer>
        </div>
        <nav className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-border bg-card px-1 py-1.5 md:hidden" aria-label="Mobile">
          {items.slice(0, 5).map(({ href, k, icon: Icon }) => (
            <Link key={href} href={href} aria-current={active(href) ? "page" : undefined}
              className={cn("flex min-w-14 flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-[11px]", active(href) ? "text-brand font-bold" : "text-muted")}>
              <Icon size={20} />{t(k)}
            </Link>
          ))}
        </nav>
      </div>
    </MeCtx.Provider>
  );
}
