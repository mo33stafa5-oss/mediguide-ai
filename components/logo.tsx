export function LogoMark({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className} role="img" aria-label="MediGuide AI">
      <defs>
        <linearGradient id="mg-g" x1="6" y1="8" x2="58" y2="58" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1677E8" /><stop offset="1" stopColor="#16C5D5" />
        </linearGradient>
      </defs>
      <path d="M32 56S6 40.5 6 21.5C6 13.5 12 8 19.2 8c5 0 9.1 2.6 12.8 7.6C35.700 10.600 39.800 8 44.800 8 52 8 58 13.500 58 21.500 58 40.500 32 56 32 56Z"
        stroke="url(#mg-g)" strokeWidth="5" strokeLinejoin="round" />
      <path d="M12 32h11l4-10 7 20 5-14 3 4h10" stroke="url(#mg-g)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo({ size = 36, withText = true, ar = false }: { size?: number; withText?: boolean; ar?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark size={size} />
      {withText && (
        <span className="font-extrabold tracking-tight text-navy" style={{ fontSize: size * 0.55 }} dir="ltr">
          MediGuide <span className="text-brand">AI</span>
          {ar && <span className="sr-only">ميدي جايد</span>}
        </span>
      )}
    </span>
  );
}
