// Decorative illustration: assistant bot + pulse card (original SVG).
export function HeroArt() {
  return (
    <svg viewBox="0 0 420 360" className="mx-auto w-full max-w-md animate-float" role="img" aria-label="MediGuide AI assistant illustration">
      <defs>
        <linearGradient id="ha" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#1677E8" /><stop offset="1" stopColor="#16C5D5" /></linearGradient>
      </defs>
      <rect x="20" y="40" width="380" height="280" rx="32" fill="var(--card)" stroke="var(--border)" />
      <path d="M40 220h70l24-60 40 120 30-80 20 24h120" stroke="url(#ha)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" fill="none" className="animate-pulse-line" />
      <rect x="40" y="70" width="140" height="14" rx="7" fill="var(--soft)" /><rect x="40" y="94" width="90" height="10" rx="5" fill="var(--soft)" />
      <g transform="translate(250 60)">
        <rect x="0" y="20" width="110" height="90" rx="28" fill="url(#ha)" />
        <rect x="14" y="36" width="82" height="52" rx="18" fill="#102A56" />
        <circle cx="40" cy="60" r="7" fill="#7FE9F2" /><circle cx="70" cy="60" r="7" fill="#7FE9F2" />
        <path d="M44 76q11 8 22 0" stroke="#7FE9F2" strokeWidth="4" strokeLinecap="round" fill="none" />
        <line x1="55" y1="20" x2="55" y2="2" stroke="#1677E8" strokeWidth="4" /><circle cx="55" cy="2" r="5" fill="#16C5D5" />
        <path d="M55 128s-26-15-26-34c0-8 6-14 13-14 5 0 9 3 13 8 4-5 8-8 13-8 7 0 13 6 13 14 0 19-26 34-26 34Z" transform="translate(0 12) scale(.9)" fill="#fff" stroke="url(#ha)" strokeWidth="5" />
      </g>
      <rect x="40" y="270" width="320" height="32" rx="16" fill="var(--soft)" />
    </svg>
  );
}
