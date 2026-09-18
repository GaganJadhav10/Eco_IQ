import React, { useState } from "react";
import { Braces, Copy, ExternalLink, FileText, ShieldCheck, ShieldX } from "lucide-react";
import { api } from "../../lib/api.js";
import { SOURCE_LABEL, VARIABLES, varLabel } from "../../lib/labels.js";
import Markdown from "../Markdown.jsx";
import { Badge, SectionTitle } from "../ui.jsx";

export default function DataTab({ result }) {
  const [raw, setRaw] = useState(false);
  const a = result.assessment;
  const site = result.site_state;
  const n = result.narration;
  const guardOk = n.guard ? n.guard.some((g) => g.passed) : null;
  const inputs = Object.keys(VARIABLES).filter((k) => site[k] != null);

  return (
    <div className="grid gap-4 xl:grid-cols-5">
      <div className="space-y-4 xl:col-span-3">
        <section className="card p-5">
          <SectionTitle icon={FileText} title="Scientific narration"
                        subtitle={n.mode === "llm" ? "Rephrased by the LLM and checked by the numeric guard" : "Generated deterministically from the assessment"}
                        right={
                          <Badge tone={n.mode === "llm" ? "forest" : n.mode === "template_fallback" ? "ochre" : "neutral"} icon={guardOk === false ? ShieldX : ShieldCheck}>
                            {n.mode === "llm" ? "LLM · guard passed" : n.mode === "template_fallback" ? "LLM rejected → template" : "Template"}
                          </Badge>
                        } />
          <Markdown text={n.text} />
          {n.guard?.some((g) => !g.passed) && (
            <div className="mt-4 rounded-xl bg-ochre-100/60 p-3 text-xs text-[#6f4b04]">
              <strong>Guard report:</strong>{" "}
              {n.guard.map((g, i) => (
                <span key={i}>attempt {i + 1}: {g.passed ? "passed" : `rejected (numbers: ${(g.unsupported_numbers || []).join(", ") || "none"}; identifiers: ${(g.unsupported_identifiers || []).join(", ") || "none"})`}{i < n.guard.length - 1 ? " · " : ""}</span>
              ))}
            </div>
          )}
        </section>
      </div>
      <div className="space-y-4 xl:col-span-2">
        <section className="card p-5">
          <SectionTitle title="Printable report" subtitle="Diagnosis, plan, evidence and confidence in one document" />
          <a href={api.reportUrl(result.assessment_id)} target="_blank" rel="noreferrer" className="btn-primary w-full">
            <ExternalLink className="h-4 w-4" /> Open report (print to PDF)
          </a>
        </section>
        <section className="card p-5">
          <SectionTitle title="Inputs used" subtitle="Where each value came from" />
          <ul className="divide-y divide-sand-100 text-sm">
            {inputs.map((k) => (
              <li key={k} className="flex items-center justify-between gap-2 py-1.5">
                <span className="text-ink-600">{varLabel(k)}</span>
                <span className="flex items-center gap-2">
                  <strong className="text-ink-900">{String(site[k]).replace(/_/g, " ")}</strong>
                  {site.field_sources?.[k] && <span className="text-[10px] text-ink-400">{SOURCE_LABEL[site.field_sources[k]]}</span>}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card p-5">
          <SectionTitle icon={Braces} title="Raw Assessment object" subtitle="The single authoritative output everything else is rendered from"
                        right={<button className="btn-ghost py-1 text-xs" onClick={() => navigator.clipboard?.writeText(JSON.stringify(a, null, 2))}><Copy className="h-3.5 w-3.5" />Copy</button>} />
          <button className="btn-ghost w-full" onClick={() => setRaw(!raw)}>{raw ? "Hide" : "Show"} JSON</button>
          {raw && <pre className="scroll-thin mt-3 max-h-[480px] overflow-auto rounded-xl bg-forest-950 p-3 text-[11px] leading-relaxed text-leaf-100">{JSON.stringify(a, null, 2)}</pre>}
        </section>
      </div>
    </div>
  );
}
