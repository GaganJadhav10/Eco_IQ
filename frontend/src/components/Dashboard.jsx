import React, { useEffect, useState } from "react";
import { BarChart3, FileText, FlaskConical, LayoutDashboard, ListOrdered, MapPin } from "lucide-react";
import { CONCERNS, humanize } from "../lib/labels.js";
import { api } from "../lib/api.js";
import DataTab from "./tabs/DataTab.jsx";
import EvidenceTab from "./tabs/EvidenceTab.jsx";
import OverviewTab from "./tabs/OverviewTab.jsx";
import PlanTab from "./tabs/PlanTab.jsx";
import TrendsTab from "./tabs/TrendsTab.jsx";
import { Badge } from "./ui.jsx";

const SECTIONS = [
  { id: "diagnosis", label: "What's holding it back", icon: LayoutDashboard },
  { id: "plan", label: "What to do, in order", icon: ListOrdered },
  { id: "evidence", label: "The evidence", icon: FlaskConical },
  { id: "trends", label: "History", icon: BarChart3 },
  { id: "report", label: "Full write-up", icon: FileText },
];

function jump(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function SectionHeading({ id, index, title, blurb, icon: Icon }) {
  return (
    <div id={id} className="scroll-mt-28 pt-2">
      <div className="flex items-center gap-2 text-forest-700">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-leaf-100"><Icon className="h-4 w-4" /></span>
        <span className="label text-forest-700">Part {index}</span>
      </div>
      <h3 className="mt-1.5 font-display text-xl font-semibold text-ink-900">{title}</h3>
      <p className="mt-1 max-w-2xl text-sm text-ink-600">{blurb}</p>
    </div>
  );
}

export default function Dashboard({ result }) {
  const [active, setActive] = useState("diagnosis");
  const a = result.assessment;
  const site = result.site_state;
  const insufficient = a.status === "insufficient_data";

  // Highlight the section currently in view in the jump bar.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-25% 0px -65% 0px" },
    );
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [result.assessment_id, insufficient]);

  const shown = insufficient ? SECTIONS.filter((s) => ["diagnosis", "report"].includes(s.id)) : SECTIONS;

  return (
    <div className="space-y-10" key={result.assessment_id}>
      {/* site summary */}
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
        <div className="min-w-0">
          <h2 className="truncate font-display text-2xl font-semibold text-ink-900">
            {site.name || (a.site_id.startsWith("chat_") || a.site_id === "adhoc" ? "Your land" : humanize(a.site_id))}
          </h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {site.climate_zone && (
              <Badge tone="leaf" icon={MapPin} title={`from ${site.field_sources?.climate_zone || "input"}`}>
                {humanize(site.climate_zone)}
                {site.field_sources?.climate_zone === "geo_lookup" && " · from coordinates"}
              </Badge>
            )}
            {site.concern && <Badge>{CONCERNS[site.concern] || humanize(site.concern)}</Badge>}
            {site.crop_system && <Badge>{humanize(site.crop_system)}</Badge>}
            <Badge tone={insufficient ? "ochre" : "forest"}>{insufficient ? "Needs more data" : "Complete"}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={`rounded-2xl border px-4 py-2 text-center ${a.confidence.level === "high" ? "border-forest-500/30 bg-leaf-50" : a.confidence.level === "moderate" ? "border-ochre-500/30 bg-ochre-100/60" : "border-clay-500/30 bg-clay-100/60"}`}>
            <div className="label">How sure</div>
            <div className={`font-display text-xl font-semibold capitalize ${a.confidence.level === "high" ? "text-forest-700" : a.confidence.level === "moderate" ? "text-[#8a5d05]" : "text-clay-500"}`}>
              {a.confidence.level}
            </div>
          </div>
          <a href={api.reportUrl(result.assessment_id)} target="_blank" rel="noreferrer" className="btn-ghost">
            <FileText className="h-4 w-4" /> Print
          </a>
        </div>
      </div>

      {/* jump bar */}
      <nav className="sticky top-[68px] z-20 -mx-1 overflow-x-auto rounded-2xl border border-sand-200 bg-white/90 p-1.5 backdrop-blur">
        <div className="flex gap-1">
          {shown.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => jump(id)}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-semibold transition ${active === id ? "bg-forest-800 text-white" : "text-ink-600 hover:bg-sand-100"}`}>
              <Icon className="h-4 w-4" />{label}
            </button>
          ))}
        </div>
      </nav>

      <section className="space-y-4">
        <SectionHeading id="diagnosis" index={1} icon={LayoutDashboard}
                        title={insufficient ? "Not enough to go on yet" : "What's holding this land back"}
                        blurb={insufficient
                          ? "Some essential facts are missing. Rather than guess, EcoIQ lists what each one would settle."
                          : "The scarcest factor sets the ceiling. Below it are the ranked explanations for your concern, each with the chain of cause and effect behind it."} />
        <OverviewTab result={result} onNavigate={jump} />
      </section>

      {!insufficient && (
        <>
          <section className="space-y-4">
            <SectionHeading id="plan" index={2} icon={ListOrdered} title="What to do, in order"
                            blurb="Ordered by what has to happen first. Anything that would compete for scarce water is deliberately held back, and says so." />
            <PlanTab result={result} onNavigate={jump} />
          </section>

          <section className="space-y-4">
            <SectionHeading id="evidence" index={3} icon={FlaskConical} title="The evidence behind it"
                            blurb="Every study that applies here, and every study thrown out, with the reason it did not fit this land." />
            <EvidenceTab result={result} />
          </section>

          <section className="space-y-4">
            <SectionHeading id="trends" index={4} icon={BarChart3} title="How this land has changed"
                            blurb="When several indicators fall together, that strengthens the matching explanation." />
            <TrendsTab result={result} />
          </section>
        </>
      )}

      <section className="space-y-4">
        <SectionHeading id="report" index={insufficient ? 2 : 5} icon={FileText} title="The full write-up"
                        blurb="The complete explanation, where each input came from, and a printable report you can share." />
        <DataTab result={result} />
      </section>
    </div>
  );
}
