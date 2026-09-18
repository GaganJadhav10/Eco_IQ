import React from "react";
import { ArrowRight, Binoculars, CircleAlert, Gauge as GaugeIcon, GitBranch, Lightbulb, Scale, TrendingDown, TrendingUp } from "lucide-react";
import { SOURCE_LABEL, intLabel, varLabel } from "../../lib/labels.js";
import { Badge, Gauge, ScoreBar, SectionTitle, Stat } from "../ui.jsx";

function TrendIcon({ trend }) {
  if (trend === "declining") return <Badge tone="clay" icon={TrendingDown}>declining</Badge>;
  if (trend === "improving") return <Badge tone="forest" icon={TrendingUp}>improving</Badge>;
  if (trend === "stable") return <Badge>stable</Badge>;
  return null;
}

function Insufficient({ a }) {
  return (
    <div className="card overflow-hidden">
      <div className="topo bg-forest-900 p-6 text-white">
        <div className="flex items-center gap-2 text-ochre-100"><CircleAlert className="h-5 w-5" /><span className="font-semibold">Recommendation withheld</span></div>
        <p className="mt-2 max-w-2xl text-white/75">
          Critical inputs are missing. Rather than guess, EcoIQ lists exactly what each one would unlock.
          Answer the questions in the chat or fill in the form.
        </p>
      </div>
      <ul className="divide-y divide-sand-100">
        {a.missing_variables.map((v) => (
          <li key={v} className="flex gap-3 p-4">
            <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-ochre-100 text-[#8a5d05]"><Binoculars className="h-4 w-4" /></span>
            <div>
              <div className="font-semibold text-ink-900">{varLabel(v)}</div>
              <p className="text-sm text-ink-600">{a.missing_variable_impact?.[v]}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SharpenCard({ result }) {
  const qs = result.improvement_questions || [];
  const impact = result.improvement_impact || {};
  if (qs.length === 0) return null;
  return (
    <section className="card border-forest-500/25 bg-gradient-to-br from-leaf-50 to-white p-5">
      <SectionTitle icon={Binoculars} title="Sharpen this assessment"
                    subtitle="Answer in the chat and the diagnosis is recomputed with the extra data" />
      <ul className="space-y-2 text-sm text-ink-900">
        {qs.map((q) => <li key={q} className="flex gap-2"><span className="text-forest-600">?</span>{q}</li>)}
      </ul>
      {Object.keys(impact).length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-sand-100 pt-2">
          {Object.entries(impact).map(([v, why]) => (
            <li key={v} className="text-xs text-ink-600"><code>{v}</code>: {why}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function OverviewTab({ result, onNavigate }) {
  const a = result.assessment;
  const site = result.site_state;
  if (a.status === "insufficient_data") {
    return (
      <div className="space-y-4">
        <Insufficient a={a} />
        <ConfidenceCard a={a} />
      </div>
    );
  }
  const lf = a.limiting_factor;
  const lfDriver = a.drivers_ranked.find((d) => d.variable === lf);
  const top = a.drivers_ranked.filter((d) => d.supports_concern);
  const maxRank = Math.max(...a.drivers_ranked.map((d) => d.rank_score), 0.001);

  return (
    <div className="grid gap-4 xl:grid-cols-5">
      <div className="space-y-4 xl:col-span-3">
        <section className="topo relative overflow-hidden rounded-2xl bg-forest-900 p-5 text-white shadow-lift sm:p-6">
          <div className="flex flex-wrap items-center gap-6">
            <Gauge value={a.suitability[lf]} label="suitability" />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold uppercase tracking-wider text-leaf-300">Limiting constraint</div>
              <div className="mt-1 font-display text-3xl font-semibold leading-tight">{varLabel(lf)}</div>
              <p className="mt-2 text-sm leading-relaxed text-white/70">
                The scarcest factor with a recorded pathway to your concern. Following Liebig’s law of the minimum,
                improving other factors pays off less until this one is addressed.
              </p>
              {lfDriver && (
                <div className="mt-3 flex flex-wrap items-center gap-1 text-xs text-white/80">
                  {lfDriver.path.map((p, i) => (
                    <React.Fragment key={p}>
                      {i > 0 && <ArrowRight className="h-3 w-3 text-white/40" />}
                      <span className="rounded-md bg-white/10 px-2 py-0.5">{varLabel(p)}</span>
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>
          </div>
          {a.sequence_detail?.[0] && (
            <button onClick={() => onNavigate("plan")} className="mt-5 flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left transition hover:bg-white/10">
              <span className="text-sm"><span className="text-white/60">Start with </span><strong>{intLabel(a.sequence_detail[0].intervention)}</strong></span>
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-leaf-300">View plan <ArrowRight className="h-3 w-3" /></span>
            </button>
          )}
        </section>

        {(a.hypothesis_note || a.discriminating_measurement || a.under_determined) && (
          <section className="card border-ochre-500/30 bg-gradient-to-br from-ochre-100/60 to-white p-5">
            <SectionTitle icon={Scale} title="Weighing the explanations" subtitle="Ranked hypotheses, not verdicts" />
            <div className="space-y-3 text-sm leading-relaxed text-ink-900">
              {a.under_determined && <p className="font-medium">The current data can’t separate the top two explanations.</p>}
              {a.hypothesis_note && <p>{a.hypothesis_note}</p>}
              {a.discriminating_measurement && (
                <div className="flex gap-2 rounded-xl bg-white/80 p-3">
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-ochre-500" />
                  <p><strong>What would settle it: </strong>{a.discriminating_measurement}</p>
                </div>
              )}
            </div>
          </section>
        )}

        <section className="card p-5">
          <SectionTitle icon={GitBranch} title="Ranked drivers" subtitle="How strongly each factor explains your concern (severity × pathway strength × trend)" />
          <ul className="space-y-3">
            {a.drivers_ranked.slice(0, 6).map((d, i) => (
              <li key={d.variable} className={`rounded-xl border p-3 transition ${d.supports_concern ? "border-sand-200 bg-white" : "border-dashed border-sand-200 bg-sand-50 opacity-70"}`} title={d.assumption}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="grid h-6 w-6 place-items-center rounded-full bg-sand-100 text-xs font-bold text-ink-600">{i + 1}</span>
                    <span className="font-semibold text-ink-900">{varLabel(d.variable)}</span>
                    {d.variable === lf && <Badge tone="clay">limiting</Badge>}
                    <TrendIcon trend={d.temporal_trend} />
                  </div>
                  <span className="text-xs tabular-nums text-ink-600">rank {d.rank_score} · suitability {d.suitability_score}</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-sand-100">
                  <div className="h-full rounded-full bg-gradient-to-r from-forest-600 to-leaf-400" style={{ width: `${(d.rank_score / maxRank) * 100}%` }} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-1 text-xs text-ink-600">
                  {d.path.map((p, j) => (
                    <React.Fragment key={p}>
                      {j > 0 && <ArrowRight className="h-3 w-3 text-ink-400" />}
                      <span>{varLabel(p)}</span>
                    </React.Fragment>
                  ))}
                  <span className="ml-1 text-ink-400">· {d.source_ids.join(", ")}</span>
                </div>
              </li>
            ))}
          </ul>
          {top.length === 0 && <p className="text-sm text-ink-600">No driver currently supports the concern.</p>}
        </section>
      </div>

      <div className="space-y-4 xl:col-span-2">
        <ConfidenceCard a={a} />
        <SharpenCard result={result} />
        <section className="card p-5">
          <SectionTitle icon={GaugeIcon} title="Suitability profile" subtitle="0 = limiting · 1 = adequate" />
          <ul className="space-y-2.5">
            {Object.entries(a.suitability).sort((x, y) => x[1] - y[1]).map(([k, v]) => (
              <li key={k}>
                <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                  <span className={`truncate ${k === lf ? "font-bold text-ink-900" : "text-ink-600"}`}>{varLabel(k)}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    {site.field_sources?.[k] && <span className="text-[10px] text-ink-400">{SOURCE_LABEL[site.field_sources[k]]}</span>}
                    <span className="w-8 text-right font-semibold tabular-nums text-ink-900">{v}</span>
                  </span>
                </div>
                <ScoreBar value={v} />
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

export function ConfidenceCard({ a }) {
  const c = a.confidence;
  return (
    <section className="card p-5">
      <SectionTitle icon={Scale} title="Why this confidence" subtitle="Decomposed, never a single opaque number" />
      <div className="grid grid-cols-2 gap-2">
        <Stat value={c.n_supporting_claims} label="supporting claims" />
        <Stat value={c.context_quality_mean} label="mean context match" />
        <Stat value={c.data_completeness} label="data completeness" />
        <Stat value={c.n_conflicts} label="conflicting claims" />
      </div>
      <ul className="mt-3 space-y-1.5">
        {c.rationale.map((r) => (
          <li key={r} className="flex gap-2 text-xs leading-relaxed text-ink-600">
            <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${r.includes("(-") ? "bg-clay-500" : r.includes("(+0)") ? "bg-sand-200" : "bg-forest-500"}`} />
            {r}
          </li>
        ))}
      </ul>
    </section>
  );
}
