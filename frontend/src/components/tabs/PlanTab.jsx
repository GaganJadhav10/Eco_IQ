import React, { useState } from "react";
import { ArrowUpRight, BookMarked, ChevronDown, Clock, Hourglass, Target, TriangleAlert } from "lucide-react";
import { STAGES, intLabel, varLabel } from "../../lib/labels.js";
import { Badge, SectionTitle } from "../ui.jsx";

const STAGE_STYLE = {
  forest: { dot: "bg-forest-700 text-white", ring: "border-forest-500/30", head: "text-forest-700" },
  leaf: { dot: "bg-leaf-400 text-forest-950", ring: "border-leaf-400/40", head: "text-forest-600" },
  ochre: { dot: "bg-ochre-500 text-white", ring: "border-ochre-500/40", head: "text-[#8a5d05]" },
};

function Step({ s, a, last }) {
  const [open, setOpen] = useState(false);
  const stage = STAGES[s.stage] || { label: s.stage, tone: "leaf" };
  const st = STAGE_STYLE[stage.tone];
  const passages = a.supporting_passages?.[s.intervention] || [];
  const claims = [...a.eligible_claims].filter((c) => s.claim_ids.includes(c.claim_id));
  return (
    <li className="relative pl-12">
      {!last && <span className="absolute left-[17px] top-10 h-[calc(100%-1rem)] w-px bg-sand-200" />}
      <span className={`absolute left-0 top-1 grid h-9 w-9 place-items-center rounded-full font-display text-sm font-semibold shadow-soft ${st.dot}`}>{s.order}</span>
      <div className={`card border ${st.ring} p-4`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className={`text-[11px] font-semibold uppercase tracking-wider ${st.head}`}>{stage.label}</div>
            <h4 className="mt-0.5 font-display text-lg font-semibold text-ink-900">{intLabel(s.intervention)}</h4>
          </div>
          <Badge tone={s.time_horizon === "short" ? "forest" : s.time_horizon === "medium" ? "leaf" : "neutral"} icon={Clock}>
            {s.time_horizon}-term
          </Badge>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {s.target_metrics.map((m) => <Badge key={m} tone="leaf" icon={ArrowUpRight}>{varLabel(m)}</Badge>)}
        </div>
        {(s.metric_targets?.length > 0 || s.evidence_effects?.length > 0) && (
          <div className="mt-3 rounded-xl border border-sand-200 bg-sand-50 p-3">
            <div className="label mb-1.5 flex items-center gap-1"><Target className="h-3 w-3" />Measurable outcome</div>
            <ul className="space-y-1 text-sm">
              {s.metric_targets?.map((t) => (
                <li key={t.variable} className="flex flex-wrap items-baseline gap-1.5">
                  <span className="text-ink-600">{varLabel(t.variable)}:</span>
                  <span className="font-semibold text-ink-900">
                    {t.current ?? "not measured"} → {t.target}{t.unit ? ` ${t.unit}` : ""}
                  </span>
                  <span className="text-[11px] text-ink-400" title={t.note}>target from {t.source_id}</span>
                </li>
              ))}
              {s.evidence_effects?.map((e) => (
                <li key={e.claim_id} className="flex flex-wrap items-baseline gap-1.5">
                  <span className="text-ink-600">Reported effect:</span>
                  <span className="font-semibold text-forest-700">
                    {e.effect_min}–{e.effect_max} {e.effect_unit}
                  </span>
                  <span className="text-[11px] text-ink-400">{e.claim_id} · {e.time_horizon} term</span>
                  {!e.verified && <Badge tone="ochre">unverified</Badge>}
                </li>
              ))}
              {s.evidence_effects?.length === 0 && (
                <li className="text-xs text-ink-400">
                  No quantified effect size applies in this context; the evidence supports the direction of change.
                </li>
              )}
            </ul>
          </div>
        )}
        <p className={`mt-3 text-sm leading-relaxed ${s.stage.startsWith("defer") ? "text-[#6f4b04]" : "text-ink-600"}`}>
          {s.stage.startsWith("defer") && <Hourglass className="mr-1 inline h-3.5 w-3.5" />}
          {s.rationale}
        </p>
        <button onClick={() => setOpen(!open)} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-forest-600 hover:text-forest-700">
          <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "rotate-180" : ""}`} />
          Mechanism & evidence ({claims.length} claim{claims.length === 1 ? "" : "s"})
        </button>
        {open && (
          <div className="mt-3 space-y-3 border-t border-sand-100 pt-3">
            {claims.map((c) => (
              <div key={c.claim_id} className="rounded-xl bg-sand-50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-mono text-xs text-ink-400">{c.claim_id}</span>
                  <Badge tone={c.direction === "increase" ? "forest" : "clay"}>{c.direction} {varLabel(c.target_metric)}</Badge>
                  {!c.verified && <Badge tone="ochre" title="Not yet checked against the source document">unverified</Badge>}
                </div>
                <p className="mt-1.5 leading-relaxed text-ink-600">{c.mechanism}</p>
                <p className="mt-1 flex items-start gap-1 text-xs italic text-ink-400"><BookMarked className="mt-0.5 h-3 w-3 shrink-0" />{c.source_title}</p>
              </div>
            ))}
            {passages.length > 0 && (
              <div>
                <div className="label mb-1">Related causal mechanisms (semantic retrieval)</div>
                <ul className="space-y-1">
                  {passages.map((p) => (
                    <li key={p.id} className="text-xs leading-relaxed text-ink-600">
                      <span className="font-mono text-ink-400">{p.id}</span> {p.text} <span className="text-ink-400">({p.source_id})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

export default function PlanTab({ result, onNavigate }) {
  const a = result.assessment;
  if (!a.sequence_detail?.length) {
    return <div className="card p-8 text-center text-ink-600">No action plan yet. Critical data is missing (see Diagnosis).</div>;
  }
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <section className="xl:col-span-2">
        <SectionTitle title="Sequenced action plan" subtitle="Ordered by what has to happen first, not by how often an intervention is recommended" />
        <ol className="space-y-4">
          {a.sequence_detail.map((s, i) => <Step key={s.intervention} s={s} a={a} last={i === a.sequence_detail.length - 1} />)}
        </ol>
      </section>
      <aside className="space-y-4">
        {a.transfer_warnings?.length > 0 && (
          <section className="card border-clay-500/30 bg-gradient-to-br from-clay-100/70 to-white p-5">
            <SectionTitle icon={TriangleAlert} title="Evidence transfer warnings" subtitle="Direction supported; magnitude may not apply here" />
            <ul className="space-y-2">
              {a.transfer_warnings.map((w) => <li key={w} className="text-sm leading-relaxed text-ink-900">{w}</li>)}
            </ul>
          </section>
        )}
        <section className="card p-5">
          <SectionTitle title="How the order is decided" />
          <ol className="space-y-2 text-sm text-ink-600">
            <li><strong className="text-forest-700">First:</strong> interventions that improve the limiting constraint or the next step on its pathway.</li>
            <li><strong className="text-forest-600">Then:</strong> interventions acting on the other ranked drivers.</li>
            <li><strong className="text-[#8a5d05]">Later:</strong> if soil water is scarce, anything that establishes new water-demanding biomass (trees, cover crops) waits.</li>
            <li className="text-xs text-ink-400">Interventions for pressures that are absent or unobserved are not recommended.</li>
          </ol>
          <button onClick={() => onNavigate("evidence")} className="btn-ghost mt-4 w-full">Inspect all evidence</button>
        </section>
      </aside>
    </div>
  );
}
