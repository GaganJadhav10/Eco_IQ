import React from "react";
import { ArrowRight, CircleHelp, Droplets, FlaskConical, GitBranch, ListOrdered, ScanSearch, Sprout, TriangleAlert } from "lucide-react";

const SCENARIO_META = {
  beed_wheat: { icon: Droplets, tag: "Sequenced response" },
  anantapur_groundnut: { icon: CircleHelp, tag: "Hypothesis tested" },
  dharwad_cotton: { icon: TriangleAlert, tag: "Evidence transfer" },
  unknown_plot: { icon: ScanSearch, tag: "Insufficient data" },
};
const ORDER = ["beed_wheat", "anantapur_groundnut", "dharwad_cotton", "unknown_plot"];

const STEPS = [
  { icon: Sprout, title: "Understand the site", text: "Your message or form becomes structured site data. Nothing is guessed." },
  { icon: GitBranch, title: "Diagnose", text: "Scores each factor, finds the limiting one, ranks causal pathways." },
  { icon: FlaskConical, title: "Filter evidence", text: "Studies from the wrong context are rejected, and you can see why." },
  { icon: ListOrdered, title: "Sequence actions", text: "Relieve the binding constraint first, then build on it." },
];

export default function Examples({ sites, onPickSite, busy }) {
  const rank = (id) => (ORDER.includes(id) ? ORDER.indexOf(id) : ORDER.length);
  const ordered = [...sites].sort((a, b) => rank(a.site_id) - rank(b.site_id));

  return (
    <div className="space-y-10">
      <div>
        <div className="text-center">
          <span className="label">How it works</span>
          <h2 className="mt-1 font-display text-3xl font-semibold text-ink-900">Four steps, none of them guesswork</h2>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <div key={title} className="card p-4">
              <div className="flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-leaf-100 text-forest-700"><Icon className="h-4 w-4" /></span>
                <span className="label">Step {i + 1}</span>
              </div>
              <div className="mt-2 font-semibold text-ink-900">{title}</div>
              <p className="mt-1 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-center">
          <span className="label">Worked examples</span>
          <h2 className="mt-1 font-display text-3xl font-semibold text-ink-900">See it reason on a real site</h2>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-ink-600">
            Four farms, four different situations. Tap one and the full assessment appears below, exactly as it
            would for your own land.
          </p>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {ordered.map((s) => {
            const meta = SCENARIO_META[s.site_id] || { icon: Sprout, tag: "Demo site" };
            const Icon = meta.icon;
            return (
              <button key={s.site_id} disabled={busy} onClick={() => onPickSite(s)}
                      className="group card flex flex-col p-4 text-left transition hover:-translate-y-0.5 hover:border-forest-500 disabled:opacity-60">
                <div className="flex items-center justify-between gap-2">
                  <span className="grid h-9 w-9 place-items-center rounded-xl bg-leaf-100 text-forest-700">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-400">{meta.tag}</span>
                </div>
                <div className="mt-3 text-sm font-semibold leading-snug text-ink-900">{s.name}</div>
                <p className="mt-1 line-clamp-3 flex-1 text-xs leading-relaxed text-ink-600">{s.demo_purpose}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-forest-600">
                  Run this scenario <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" />
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
