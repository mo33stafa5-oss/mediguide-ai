import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import { Providers } from "@/lib/i18n/provider";
import type { Locale } from "@/lib/i18n/dict";
import "./globals.css";

export const metadata: Metadata = {
  title: "MediGuide AI — ميدي جايد",
  description: "Educational cardiovascular health assistant. مساعد تعليمي لصحة القلب.",
  icons: { icon: "/icon.svg" },
};
export const viewport: Viewport = { themeColor: "#1677e8", width: "device-width", initialScale: 1 };

const themeScript = `try{var s=localStorage.getItem('theme');if(s==='dark'||(!s&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const c = await cookies();
  const locale: Locale = c.get("locale")?.value === "en" ? "en" : "ar";
  return (
    <html lang={locale} dir={locale === "ar" ? "rtl" : "ltr"} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body>
        <Providers initialLocale={locale}>{children}</Providers>
      </body>
    </html>
  );
}
