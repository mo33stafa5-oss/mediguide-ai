"use client";
import { Languages, Moon, Sun } from "lucide-react";
import { useI18n } from "@/lib/i18n/provider";
import { Button } from "@/components/ui";

export function LangToggle() {
  const { locale, setLocale, t } = useI18n();
  return (
    <Button variant="ghost" size="sm" onClick={() => setLocale(locale === "ar" ? "en" : "ar")} aria-label="Switch language" data-testid="lang-toggle">
      <Languages size={16} /> {t("langToggle")}
    </Button>
  );
}

export function ThemeToggle() {
  const { theme, toggleTheme, t } = useI18n();
  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={t("themeToggle")} data-testid="theme-toggle">
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </Button>
  );
}

export function Disclaimer() {
  const { t } = useI18n();
  return <p className="text-xs text-muted">{t("disclaimerShort")}</p>;
}
