"use client";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { dict, type Key, type Locale } from "./dict";

type Ctx = { locale: Locale; t: (k: Key) => string; setLocale: (l: Locale) => void; theme: "light" | "dark"; toggleTheme: () => void };
const I18n = createContext<Ctx | null>(null);

export function Providers({ initialLocale, children }: { initialLocale: Locale; children: ReactNode }) {
  const [locale, setLoc] = useState<Locale>(initialLocale);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    try {
      const s = localStorage.getItem("theme");
      const t = s === "dark" || (!s && matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
      setTheme(t);
    } catch {}
  }, []);
  const setLocale = useCallback((l: Locale) => {
    setLoc(l);
    document.cookie = `locale=${l}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = l;
    document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
  }, []);
  const toggleTheme = useCallback(() => {
    setTheme((p) => {
      const n = p === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", n === "dark");
      try { localStorage.setItem("theme", n); } catch {}
      return n;
    });
  }, []);
  const t = useCallback((k: Key) => dict[locale][k] ?? k, [locale]);
  return <I18n.Provider value={{ locale, t, setLocale, theme, toggleTheme }}>{children}</I18n.Provider>;
}

export function useI18n() {
  const c = useContext(I18n);
  if (!c) throw new Error("useI18n outside Providers");
  return c;
}
