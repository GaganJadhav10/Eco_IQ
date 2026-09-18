import React, { useMemo, useState } from "react";
import { Braces, ClipboardList, MapPin, Play } from "lucide-react";
import { CONCERNS, GROUPS, VARIABLES, humanize } from "../lib/labels.js";

const CRITICAL = ["soc_percent", "annual_rainfall_mm", "land_use_class", "texture_class", "habitat_diversity_index"];

const EXAMPLE = {
  name: "Sorghum plot near Hyderabad",
  lat: 17.4, lon: 78.5, concern: "biodiversity_decline",
  soc_percent: 0.38, ph: 7.8, moisture_percent: 9, texture_class: "sandy",
  annual_rainfall_mm: 610, rainfall_pattern: "erratic", drought_frequency: "moderate",
  land_use_class: "monoculture", crop_system: "sorghum", cropping_intensity: "single", field_margin_present: false,
  habitat_diversity_index: 0.12, pollinator_observed: "low", pesticide_intensity: "high", fragmentation_level: "moderate",
};

function clean(values) {
  const out = {};
  Object.entries(values).forEach(([k, v]) => {
    if (v === "" || v == null) return;
    const meta = VARIABLES[k];
    if (meta?.bool) out[k] = v === true || v === "true";
    else if (meta && !meta.options && !meta.text && !meta.bool) out[k] = Number(v);
    else if (["lat", "lon"].includes(k)) out[k] = Number(v);
    else out[k] = v;
  });
  return out;
}

export default function SiteForm({ onSubmit, busy }) {
  const [values, setValues] = useState(EXAMPLE);
  const [mode, setMode] = useState("form");
  const [json, setJson] = useState("");
  const [error, setError] = useState(null);

  const known = useMemo(() => CRITICAL.filter((k) => values[k] !== "" && values[k] != null).length, [values]);
  const set = (k, v) => setValues((s) => ({ ...s, [k]: v }));

  const switchMode = (m) => {
    setError(null);
    if (m === "json") setJson(JSON.stringify({ site: { site_id: "form_site", ...clean(values) } }, null, 2));
    if (m === "form" && json) {
      try {
        const parsed = JSON.parse(json);
        setValues(parsed.site || parsed);
      } catch (e) {
        setError(`Invalid JSON: ${e.message}`);
        return;
      }
    }
    setMode(m);
  };

  const submit = () => {
    setError(null);
    try {
      const body = mode === "json" ? JSON.parse(json) : { site: { site_id: "form_site", ...clean(values) } };
      onSubmit(body.site ? body : { site: body });
    } catch (e) {
      setError(`Invalid JSON: ${e.message}`);
    }
  };

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-sand-200 bg-white px-4 py-2.5">
        <div className="inline-flex rounded-xl bg-sand-100 p-1">
          {[["form", ClipboardList, "Guided form"], ["json", Braces, "JSON"]].map(([m, Icon, label]) => (
            <button key={m} onClick={() => switchMode(m)}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition ${mode === m ? "bg-white text-forest-700 shadow-soft" : "text-ink-600 hover:text-ink-900"}`}>
              <Icon className="h-3.5 w-3.5" /> {label}
            </button>
          ))}
        </div>
        <span className="text-xs text-ink-600">{known}/{CRITICAL.length} critical fields</span>
      </div>

      <div className="scroll-thin max-h-[620px] overflow-y-auto px-4 py-4 sm:px-5">
        {mode === "json" ? (
          <div className="space-y-2">
            <p className="text-xs leading-relaxed text-ink-600">
              POST body for <code className="rounded bg-sand-100 px-1 font-mono">/api/assess</code>: a <code className="font-mono">site</code> object
              (any subset of the variables) and optional dated <code className="font-mono">measurements</code>.
            </p>
            <textarea value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false}
                      className="input h-[420px] font-mono text-xs leading-relaxed" />
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <label className="col-span-2 block">
                <span className="label">Site name</span>
                <input className="input mt-1" value={values.name || ""} onChange={(e) => set("name", e.target.value)} />
              </label>
              <label className="col-span-2 block">
                <span className="label">What worries you</span>
                <select className="input mt-1" value={values.concern || ""} onChange={(e) => set("concern", e.target.value)}>
                  {Object.entries(CONCERNS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="label inline-flex items-center gap-1"><MapPin className="h-3 w-3" />Latitude</span>
                <input className="input mt-1" type="number" step="0.01" value={values.lat ?? ""} onChange={(e) => set("lat", e.target.value)} />
              </label>
              <label className="block">
                <span className="label">Longitude</span>
                <input className="input mt-1" type="number" step="0.01" value={values.lon ?? ""} onChange={(e) => set("lon", e.target.value)} />
              </label>
            </div>

            {GROUPS.map((g) => (
              <fieldset key={g} className="rounded-2xl border border-sand-200 bg-white p-3">
                <legend className="px-1 font-display text-sm font-semibold text-ink-900">{g}</legend>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {Object.entries(VARIABLES).filter(([, m]) => m.group === g).map(([k, m]) => (
                    <label key={k} className="block">
                      <span className="flex items-center gap-1 text-xs font-medium text-ink-600">
                        {m.label}{m.unit ? <span className="text-ink-400">({m.unit})</span> : null}
                        {CRITICAL.includes(k) && <span className="text-clay-500" title="Required for a recommendation">*</span>}
                      </span>
                      {m.options ? (
                        <select className="input mt-1 py-1.5" value={values[k] ?? ""} onChange={(e) => set(k, e.target.value)}>
                          <option value="">Unknown</option>
                          {m.options.map((o) => <option key={o} value={o}>{humanize(o)}</option>)}
                        </select>
                      ) : m.bool ? (
                        <select className="input mt-1 py-1.5" value={values[k] == null ? "" : String(values[k])} onChange={(e) => set(k, e.target.value === "" ? "" : e.target.value === "true")}>
                          <option value="">Unknown</option>
                          <option value="true">Present</option>
                          <option value="false">Absent</option>
                        </select>
                      ) : (
                        <input className="input mt-1 py-1.5" type={m.text ? "text" : "number"} step="any" placeholder="Unknown"
                               value={values[k] ?? ""} onChange={(e) => set(k, e.target.value)} />
                      )}
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
        )}
        {error && <p className="mt-2 text-sm text-clay-500">{error}</p>}
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-sand-200 bg-white p-3">
        <button className="btn-ghost text-xs" onClick={() => { setValues({ concern: "biodiversity_decline" }); setJson(""); }}>Clear</button>
        <button className="btn-primary" onClick={submit} disabled={busy}>
          <Play className="h-4 w-4" /> Run assessment
        </button>
      </div>
    </div>
  );
}
