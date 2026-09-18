import React from "react";

const TONES = {
  forest: "border-forest-600/20 bg-leaf-100 text-forest-700",
  leaf: "border-leaf-400/40 bg-leaf-50 text-forest-600",
  ochre: "border-ochre-500/30 bg-ochre-100 text-[#8a5d05]",
  clay: "border-clay-500/30 bg-clay-100 text-[#9a4424]",
  neutral: "border-sand-200 bg-sand-50 text-ink-600",
  dark: "border-white/15 bg-white/10 text-white",
};

export function Badge({ tone = "neutral", icon: Icon, children, className = "", title }) {
  return (
    <span title={title} className={`chip ${TONES[tone]} ${className}`}>
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}

export function scoreTone(v) {
  if (v == null) return "neutral";
  return v < 0.34 ? "clay" : v < 0.67 ? "ochre" : "forest";
}

export function ScoreBar({ value, className = "" }) {
  const color = value < 0.34 ? "bg-clay-500" : value < 0.67 ? "bg-ochre-500" : "bg-forest-500";
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-sand-100 ${className}`}>
      <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${Math.max(3, value * 100)}%` }} />
    </div>
  );
}

export function SectionTitle({ icon: Icon, title, subtitle, right }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="mt-0.5 rounded-xl bg-leaf-100 p-2 text-forest-700">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div>
          <h3 className="font-display text-lg font-semibold leading-tight text-ink-900">{title}</h3>
          {subtitle && <p className="mt-0.5 text-sm text-ink-600">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

export function Stat({ value, label, hint }) {
  return (
    <div className="rounded-xl border border-sand-200 bg-sand-50 px-3 py-2.5" title={hint}>
      <div className="font-display text-2xl font-semibold tabular-nums text-ink-900">{value}</div>
      <div className="text-xs text-ink-600">{label}</div>
    </div>
  );
}

export function Gauge({ value, size = 132, label }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value ?? 0));
  const stroke = pct < 0.34 ? "var(--color-clay-500)" : pct < 0.67 ? "var(--color-ochre-500)" : "var(--color-leaf-400)";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgb(255 255 255 / 0.12)" strokeWidth="10" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={stroke} strokeWidth="10" strokeLinecap="round"
                strokeDasharray={c} strokeDashoffset={c * (1 - pct)} style={{ transition: "stroke-dashoffset 0.9s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
        <span className="font-display text-3xl font-semibold tabular-nums">{value ?? "–"}</span>
        {label && <span className="text-[10px] uppercase tracking-wider text-white/60">{label}</span>}
      </div>
    </div>
  );
}

export function Spinner({ className = "" }) {
  return (
    <span className={`inline-flex gap-1 ${className}`}>
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-current" style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </span>
  );
}
