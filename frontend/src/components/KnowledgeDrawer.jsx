import React, { useEffect, useState } from "react";
import { BookOpenText, ExternalLink, Search, X } from "lucide-react";
import { api } from "../lib/api.js";
import { intLabel, varLabel } from "../lib/labels.js";
import { Badge, Spinner } from "./ui.jsx";

const EXAMPLES = ["keeping water in the soil during dry spells", "bees and pollination", "trees competing with crops", "soil carbon in drylands"];

export default function KnowledgeDrawer({ open, onClose, health }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState(null);
  const [sources, setSources] = useState([]);
  const [busy, setBusy] = useState(false);
  const [scope, setScope] = useState("claims");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && sources.length === 0) api.knowledge("sources").then(setSources).catch(() => {});
  }, [open, sources.length]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const docCount = health?.collections?.doc_chunks || 0;

  const run = async (query) => {
    if (!query.trim()) return;
    setQ(query);
    setBusy(true);
    setError(null);
    try {
      setHits(await api.search(query, 8, scope));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`fixed inset-0 z-40 ${open ? "" : "pointer-events-none"}`}>
      <div onClick={onClose} className={`absolute inset-0 bg-forest-950/40 backdrop-blur-sm transition ${open ? "opacity-100" : "opacity-0"}`} />
      <aside className={`absolute right-0 top-0 flex h-full w-full max-w-lg flex-col bg-sand-50 shadow-lift transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"}`}>
        <div className="topo flex items-start justify-between gap-3 bg-forest-900 p-5 text-white">
          <div>
            <div className="flex items-center gap-2"><BookOpenText className="h-5 w-5 text-leaf-300" /><h3 className="font-display text-xl font-semibold">Knowledge base</h3></div>
            <p className="mt-1 text-sm text-white/70">
              {health?.store === "chroma" ? "ChromaDB" : "In-memory store"}
              {health?.collections && ` · ${health.collections.claims} claims · ${health.collections.relationships} causal links · ${health.collections.sources} sources`}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-white/70 hover:bg-white/10" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>

        <div className="scroll-thin flex-1 space-y-5 overflow-y-auto p-5">
          <form onSubmit={(e) => { e.preventDefault(); run(q); }} className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input className="input pl-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search mechanisms by meaning…" />
          </form>
          {docCount > 0 && (
            <div className="inline-flex rounded-xl bg-sand-100 p-1">
              {[["claims", `Claims (${health.collections.claims})`], ["docs", `Source passages (${docCount})`]].map(([id, label]) => (
                <button key={id} onClick={() => { setScope(id); setHits(null); }}
                        className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${scope === id ? "bg-white text-forest-700 shadow-soft" : "text-ink-600"}`}>
                  {label}
                </button>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => run(ex)} className="chip border-sand-200 bg-white text-ink-600 hover:border-forest-500 hover:text-forest-700">{ex}</button>
            ))}
          </div>

          {busy && <div className="text-sm text-forest-600">Searching <Spinner /></div>}
          {error && <p className="text-sm text-clay-500">{error}</p>}
          {hits && !busy && scope === "docs" && (
            <ul className="space-y-2">
              {hits.length === 0 && <li className="text-sm text-ink-600">No matching passages.</li>}
              {hits.map((h) => (
                <li key={h.id} className="card p-3">
                  <div className="flex items-center justify-between text-xs text-ink-400">
                    <span>{h.source_id} · p. {h.page}</span><span>similarity {h.score}</span>
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{h.text}</p>
                </li>
              ))}
            </ul>
          )}
          {hits && !busy && scope === "claims" && (
            <ul className="space-y-2">
              {hits.length === 0 && <li className="text-sm text-ink-600">No matches.</li>}
              {hits.map((h) => (
                <li key={h.claim_id} className="card p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-xs text-ink-400">{h.claim_id}</span>
                      <span className="text-sm font-semibold text-ink-900">{intLabel(h.intervention)}</span>
                    </div>
                    <Badge tone="leaf">{varLabel(h.target_metric)}</Badge>
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{h.mechanism}</p>
                  <div className="mt-1.5 flex items-center justify-between text-xs text-ink-400">
                    <span>{h.source_id}</span>
                    <span>similarity {h.rank}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div>
            <div className="label mb-2">Sources</div>
            <ul className="space-y-1.5">
              {sources.filter((s) => s.id !== "modelling_choice").map((s) => (
                <li key={s.id} className="flex items-start justify-between gap-2 rounded-xl bg-white px-3 py-2 text-xs shadow-soft">
                  <div>
                    <div className="font-medium leading-snug text-ink-900">{s.title}</div>
                    <div className="mt-0.5 text-ink-400">{s.publisher} · {s.year}{s.region ? ` · ${s.region}` : ""}</div>
                  </div>
                  {s.url && <a href={s.url} target="_blank" rel="noreferrer" className="shrink-0 text-forest-600 hover:text-forest-700" aria-label="Open source"><ExternalLink className="h-3.5 w-3.5" /></a>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </aside>
    </div>
  );
}
