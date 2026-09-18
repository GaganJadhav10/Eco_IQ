import React, { useMemo, useState } from "react";
import { BookMarked, CircleCheck, CircleX, Filter } from "lucide-react";
import { EVIDENCE, intLabel, varLabel } from "../../lib/labels.js";
import { Badge } from "../ui.jsx";

function ClaimCard({ c }) {
  const effect = c.effect_min != null ? `${c.effect_min}–${c.effect_max} ${c.effect_unit || ""}` : null;
  return (
    <article className={`card p-4 ${c.disqualified ? "border-dashed bg-sand-50" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-xs text-ink-400">{c.claim_id}</span>
          <span className="font-semibold text-ink-900">{intLabel(c.intervention)}</span>
          <Badge tone={c.direction === "increase" ? "forest" : "clay"}>{c.direction === "increase" ? "↑" : "↓"} {varLabel(c.target_metric)}</Badge>
        </div>
        <div className="flex flex-wrap gap-1">
          <Badge>{EVIDENCE[c.evidence_strength] || c.evidence_strength}</Badge>
          <Badge>{c.time_horizon}-term</Badge>
          {!c.verified && <Badge tone="ochre" title="Not yet checked against the source document">unverified</Badge>}
        </div>
      </div>
      {c.disqualified ? (
        <div className="mt-3 flex gap-2 rounded-xl bg-clay-100/70 p-3 text-sm text-[#7d361c]">
          <CircleX className="mt-0.5 h-4 w-4 shrink-0" />
          <span><strong>Rejected: </strong>{c.disqualify_reason}</span>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-ink-600">
          <span className="flex items-center gap-2">
            Context match
            <span className="h-1.5 w-20 overflow-hidden rounded-full bg-sand-100">
              <span className="block h-full rounded-full bg-forest-500" style={{ width: `${c.context_match_score * 100}%` }} />
            </span>
            <strong className="tabular-nums text-ink-900">{c.context_match_score}</strong>
          </span>
          {c.context_flags.map((f) => <Badge key={f} tone="ochre">{f.replace(/_/g, " ")}</Badge>)}
          {effect && <Badge tone="leaf">effect {effect}</Badge>}
        </div>
      )}
      <p className="mt-3 text-sm leading-relaxed text-ink-600">{c.mechanism}</p>
      <p className="mt-2 flex items-start gap-1.5 text-xs italic text-ink-400"><BookMarked className="mt-0.5 h-3 w-3 shrink-0" />{c.source_title}{c.page ? `, p. ${c.page}` : ""}</p>
    </article>
  );
}

export default function EvidenceTab({ result }) {
  const a = result.assessment;
  const [view, setView] = useState("eligible");
  const [metric, setMetric] = useState("all");
  const list = view === "eligible" ? a.eligible_claims : a.rejected_claims;
  const metrics = useMemo(() => [...new Set([...a.eligible_claims, ...a.rejected_claims].map((c) => c.target_metric))], [a]);
  const shown = list.filter((c) => metric === "all" || c.target_metric === metric);

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-3">
        <div className="inline-flex rounded-xl bg-sand-100 p-1">
          <button onClick={() => setView("eligible")} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition ${view === "eligible" ? "bg-white text-forest-700 shadow-soft" : "text-ink-600"}`}>
            <CircleCheck className="h-4 w-4" /> Applies here ({a.eligible_claims.length})
          </button>
          <button onClick={() => setView("rejected")} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition ${view === "rejected" ? "bg-white text-clay-500 shadow-soft" : "text-ink-600"}`}>
            <CircleX className="h-4 w-4" /> Rejected ({a.rejected_claims.length})
          </button>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-600">
          <Filter className="h-4 w-4" />
          <select className="input w-auto py-1.5" value={metric} onChange={(e) => setMetric(e.target.value)}>
            <option value="all">All metrics</option>
            {metrics.map((m) => <option key={m} value={m}>{varLabel(m)}</option>)}
          </select>
        </label>
      </div>
      {view === "rejected" && (
        <p className="px-1 text-sm text-ink-600">
          Studies whose load-bearing conditions (rainfall, soil texture, climate zone or farming system) don’t match
          this site. They’re excluded outright rather than down-weighted, and kept here so you can check the decision.
        </p>
      )}
      {shown.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-600">No claims in this view.</div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">{shown.map((c) => <ClaimCard key={c.claim_id} c={c} />)}</div>
      )}
    </div>
  );
}
