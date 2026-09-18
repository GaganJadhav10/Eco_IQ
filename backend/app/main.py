"""FastAPI app: HTTP routes only. Science lives in app/reasoning, orchestration in app/pipeline."""
from __future__ import annotations

import html
import os
from contextlib import asynccontextmanager
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.extractor import asked_about, extract
from app.llm import get_llm
from app.models import Assessment, Measurement, SiteState
from app.narrator import narrate
from app.pipeline import assess, resolve_zone
from app.retrieval.store import get_store
from app.slots import next_questions

@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # seed/open ChromaDB once, before the first request
    yield


app = FastAPI(title="EcoIQ - Evidence-Constrained Environmental Reasoning System", lifespan=lifespan)
DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

# Same-origin in production (FastAPI serves the built frontend). CORS only matters when the
# frontend dev server or a separately hosted frontend calls the API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    # Vercel gives every deployment its own preview URL, so allow that pattern too.
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- helpers
def run_assessment(site: SiteState, measurements: list[Measurement] | None = None) -> dict:
    store, llm = get_store(), get_llm()
    assessment, resolved = assess(site, store, measurements)
    narration = narrate(assessment, llm)
    aid = store.save_assessment(resolved.site_id, resolved.model_dump(), assessment.model_dump(), narration["text"])
    history = measurements if measurements is not None else store.measurements(resolved.site_id)
    return {
        "assessment_id": aid,
        "assessment": assessment.model_dump(),
        "site_state": resolved.model_dump(),
        "measurements": [m.model_dump() for m in history],
        "narration": narration,
        "questions": next_questions(assessment.missing_variables, assessment.missing_variable_impact)
        if assessment.status == "insufficient_data" else [],
        # A complete assessment still says what extra data would sharpen it.
        "improvement_questions": [] if assessment.status == "insufficient_data" else
        next_questions(assessment.missing_variables, assessment.missing_variable_impact),
        "improvement_impact": {v: assessment.missing_variable_impact.get(v, "")
                               for v in assessment.missing_variables[:4]},
    }


def intervention_focus(assessment: dict, names: list[str]) -> list[dict]:
    """Answer 'what about X?' from the assessment that was just computed - no new reasoning."""
    out = []
    for name in names:
        eligible = [c for c in assessment["eligible_claims"] if c["intervention"] == name]
        rejected = [c for c in assessment["rejected_claims"] if c["intervention"] == name]
        step = next((s for s in assessment["sequence_detail"] if s["intervention"] == name), None)
        if not eligible and not rejected and not step:
            verdict = ("No evidence for this intervention is held for the metrics on this site's causal pathways, "
                       "so it was not considered.")
        elif step:
            verdict = f"Recommended at position {step['order']} ({step['stage']}). {step['rationale']}"
        elif eligible and all(c["direction"] == "decrease" for c in eligible):
            harm = ", ".join(f"{c['target_metric']} ({c['claim_id']})" for c in eligible)
            verdict = ("The only context-valid evidence for it at this site points the wrong way: it is expected to "
                       f"decrease {harm}. It is therefore not recommended here.")
        elif eligible:
            verdict = ("Context-valid evidence exists, but it did not make the shortlist: another intervention with "
                       "stronger or better-matched evidence covers the same metrics, or the pressure it addresses "
                       "is not present here.")
        else:
            verdict = ("All evidence for it was rejected for this site: "
                       + "; ".join(c["disqualify_reason"] for c in rejected))
        out.append({"intervention": name, "in_sequence": bool(step), "verdict": verdict,
                    "eligible_claims": eligible, "rejected_claims": rejected})
    return out


def merge(state: dict, fields: dict, source: str) -> tuple[dict, list[str]]:
    state = dict(state)
    sources = dict(state.get("field_sources") or {})
    changed = []
    for k, v in fields.items():
        if v is None or k in ("field_sources", "site_id"):
            continue
        if state.get(k) != v:
            changed.append(k)
        state[k] = v
        sources[k] = source
    state["field_sources"] = sources
    return state, changed


# --------------------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    store = get_store()
    try:
        db_ok = store.ping()
    except Exception as e:  # noqa: BLE001 - health must report, not raise
        db_ok = f"error: {e.__class__.__name__}"
    return {"status": "ok", "store": store.backend, "db": db_ok, "fallback_reason": store.fallback_reason,
            "collections": store.counts() if hasattr(store, "counts") else None,
            "llm_enabled": get_llm().enabled, "llm_model": get_llm().model if get_llm().enabled else None}


class AssessRequest(BaseModel):
    site: SiteState
    measurements: list[Measurement] | None = None


@app.post("/api/assess")
def assess_structured(req: AssessRequest):
    """Structured JSON input mode. Fields supplied here are recorded with source 'json'."""
    site = req.site.model_copy(deep=True)
    for k, v in site.model_dump(exclude={"field_sources", "site_id", "name"}).items():
        if v is not None:
            site.field_sources.setdefault(k, "json")
    return run_assessment(site, req.measurements)


@app.get("/api/sites")
def list_sites():
    return get_store().list_sites()


@app.get("/api/sites/{site_id}")
def get_site(site_id: str):
    store = get_store()
    site = store.get_site(site_id)
    if not site:
        raise HTTPException(404, "site not found")
    return {"site": site.model_dump(), "measurements": [m.model_dump() for m in store.measurements(site_id)]}


@app.post("/api/sites/{site_id}/assess")
def assess_site(site_id: str):
    site = get_store().get_site(site_id)
    if not site:
        raise HTTPException(404, "site not found")
    site.field_sources = {k: "history" for k, v in site.model_dump(exclude={"field_sources"}).items()
                          if v is not None and k not in ("site_id", "name")}
    return run_assessment(site)


class ChatRequest(BaseModel):
    message: str = ""
    conversation_id: str | None = None
    site_id: str | None = None        # attach a stored site (its data + measurement history)
    site_json: dict | None = None     # structured fields sent alongside the text


@app.post("/api/chat")
def chat(req: ChatRequest):
    store, llm = get_store(), get_llm()
    cid = req.conversation_id or uuid.uuid4().hex[:12]
    conv = store.get_conversation(cid) if req.conversation_id else None
    state = (conv or {}).get("site_state") or {}
    if not state:
        state = SiteState(site_id=f"chat_{cid}").model_dump()

    if req.site_id:
        stored = store.get_site(req.site_id)
        if not stored:
            raise HTTPException(404, "site not found")
        base = stored.model_dump(exclude={"field_sources"})
        state, _ = merge(state, {k: v for k, v in base.items() if v is not None}, "history")
        state["site_id"] = req.site_id

    fields, mode = extract(req.message, llm) if req.message.strip() else ({}, "none")
    # When the site is already known, only let the text override the user's framing and values
    # it explicitly restates.
    state, changed = merge(state, fields, "user_text")
    if req.site_json:
        valid = SiteState(**{k: v for k, v in req.site_json.items() if k in SiteState.model_fields}).model_dump()
        state, changed_json = merge(state, {k: v for k, v in valid.items() if k in req.site_json}, "json")
        changed += changed_json

    site = SiteState(**state)
    result = run_assessment(site)
    store.save_conversation(cid, state)
    store.add_message(cid, "user", req.message)

    focus = intervention_focus(result["assessment"], asked_about(req.message)) if req.message.strip() else []
    result["focus"] = focus
    reply = ""
    for f in focus:
        label = f["intervention"].replace("_", " ")
        reply += f"**About {label}:** {f['verdict']}\n\n"
    reply += result["narration"]["text"]
    if result["improvement_questions"]:
        reply += "\n\n**To sharpen this assessment, you could also tell me:**\n" + \
                 "\n".join(f"- {q}" for q in result["improvement_questions"])
    if result["questions"]:
        reply += "\n\n**To continue, please tell me:**\n" + "\n".join(f"- {q}" for q in result["questions"])
    store.add_message(cid, "assistant", reply, result["assessment_id"])
    understood = {k: state[k] for k in fields if k in state}
    return {"conversation_id": cid, "reply": reply, "extraction": {"mode": mode, "fields": understood,
                                                                    "changed": sorted(set(changed))}, **result}


@app.get("/api/conversations/{cid}")
def get_conversation(cid: str):
    conv = get_store().get_conversation(cid)
    if not conv:
        raise HTTPException(404, "conversation not found")
    return conv


@app.get("/api/zone")
def zone(lat: float, lon: float):
    resolved = resolve_zone(SiteState(lat=lat, lon=lon), get_store())
    return {"lat": lat, "lon": lon, "climate_zone": resolved.climate_zone}


@app.get("/api/search")
def search(q: str, limit: int = 10, scope: str = "claims"):
    """scope=claims searches claim mechanisms; scope=docs searches indexed source documents."""
    store = get_store()
    if scope == "docs":
        return store.search_docs(q, limit) if hasattr(store, "search_docs") else []
    return store.search(q, limit)


@app.get("/api/knowledge/{kind}")
def knowledge(kind: str):
    store = get_store()
    getters = {
        "claims": lambda: [c.model_dump() for c in store.all_claims()],
        "relationships": lambda: [r.model_dump() for r in store.relationships()],
        "thresholds": lambda: [t.model_dump() for t in store.thresholds()],
        "interventions": lambda: [i.model_dump() for i in store.interventions().values()],
        "sources": lambda: [s.model_dump() for s in store.sources()],
    }
    if kind not in getters:
        raise HTTPException(404, f"unknown kind; use one of {sorted(getters)}")
    return getters[kind]()


# --------------------------------------------------------------------------- report
@app.get("/api/report/{aid}", response_class=HTMLResponse)
def report(aid: str):
    row = get_store().get_assessment(aid)
    if not row:
        raise HTTPException(404, "assessment not found")
    a = Assessment(**row["output"])
    site = row["input"]
    sources = {s.id: s for s in get_store().sources()}
    e = html.escape

    def claims_table(claims, rejected=False):
        if not claims:
            return "<p class='muted'>None.</p>"
        head = "<tr><th>ID</th><th>Intervention</th><th>Metric</th><th>Dir.</th><th>Effect</th><th>Horizon</th>" \
               f"<th>{'Reason rejected' if rejected else 'Context match'}</th><th>Evidence</th><th>Source</th></tr>"
        rows = []
        for c in claims:
            eff = f"{c.effect_min:g}-{c.effect_max:g} {e(c.effect_unit or '')}" if c.effect_min is not None else "-"
            ctx = e(c.disqualify_reason or "") if rejected else f"{c.context_match_score:g} {e(', '.join(c.context_flags))}"
            src = sources.get(c.source_id)
            link = f"<a href='{e(src.url)}'>{e(c.source_title)}</a>" if src and src.url else e(c.source_title)
            ver = "" if c.verified else " <span class='badge'>unverified</span>"
            rows.append(f"<tr><td>{c.claim_id}</td><td>{e(c.intervention)}</td><td>{e(c.target_metric)}</td>"
                        f"<td>{c.direction}</td><td>{eff}</td><td>{c.time_horizon}</td><td>{ctx}</td>"
                        f"<td>{c.evidence_strength}{ver}</td><td>{link}</td></tr>")
        return f"<table>{head}{''.join(rows)}</table>"

    def step_targets(s):
        rows = [f"{e(t.variable)}: {e(str(t.current)) if t.current is not None else 'not measured'} &rarr; "
                f"{e(str(t.target))}{e(' ' + t.unit) if t.unit else ''} <span class='muted'>({e(t.source_id)})</span>"
                for t in s.metric_targets]
        rows += [f"{e(x.claim_id)}: {x.effect_min:g}-{x.effect_max:g} {e(x.effect_unit or '')} "
                 f"({x.time_horizon} term)" + ("" if x.verified else " <span class='badge'>unverified</span>")
                 for x in s.evidence_effects]
        return "<br>".join(rows) or "<span class='muted'>direction only</span>"

    seq = "".join(f"<tr><td>{s.order}</td><td><b>{e(s.intervention)}</b></td><td>{e(s.stage)}</td>"
                  f"<td>{e(', '.join(s.target_metrics))}</td><td>{step_targets(s)}</td>"
                  f"<td>{s.time_horizon}</td><td>{e(s.rationale)}</td>"
                  f"<td>{e(', '.join(s.claim_ids))}</td></tr>" for s in a.sequence_detail)
    drivers = "".join(f"<tr><td>{e(d.variable)}</td><td>{d.suitability_score:g}</td><td>{d.rank_score:g}</td>"
                      f"<td>{e(d.temporal_trend or '-')}</td><td>{e(' -> '.join(d.path))}</td></tr>"
                      for d in a.drivers_ranked)
    missing = "".join(f"<li><code>{e(v)}</code>: {e(a.missing_variable_impact.get(v, ''))}</li>"
                      for v in a.missing_variables)
    c = a.confidence
    body = f"""
<h1>Site assessment: {e(site.get('name') or a.site_id)}</h1>
<p class='muted'>Assessment {e(aid)} · climate zone {e(str(site.get('climate_zone')))} · status {a.status} ·
All content below is computed deterministically from the knowledge base; no language model generated it.</p>
<button onclick='window.print()'>Print / save as PDF</button>
<h2>1. Diagnosis</h2>
<p><b>Limiting constraint:</b> {e(str(a.limiting_factor))}</p>
{f"<p><b>Your hypothesis:</b> {e(a.hypothesis_note)}</p>" if a.hypothesis_note else ""}
{f"<p><b>Discriminating measurement:</b> {e(a.discriminating_measurement)}</p>" if a.discriminating_measurement else ""}
<table><tr><th>Driver</th><th>Suitability</th><th>Rank score</th><th>Trend</th><th>Causal pathway</th></tr>{drivers}</table>
<h2>2. Recommendations (sequenced)</h2>
{f"<table><tr><th>#</th><th>Intervention</th><th>Stage</th><th>Impacted metrics</th><th>Measurable target / reported effect</th><th>Horizon</th><th>Why</th><th>Evidence</th></tr>{seq}</table>" if seq else "<p>No recommendation produced.</p>"}
<h2>3. Evidence transfer warnings</h2>
{"<ul>" + "".join(f"<li>{e(w)}</li>" for w in a.transfer_warnings) + "</ul>" if a.transfer_warnings else "<p class='muted'>None.</p>"}
<h2>4. Confidence: {c.level}</h2>
<p>Supporting claims {c.n_supporting_claims} · mean context match {c.context_quality_mean:g} ·
data completeness {c.data_completeness:g} · conflicts {c.n_conflicts}</p>
<ul>{"".join(f"<li>{e(r)}</li>" for r in c.rationale)}</ul>
<h2>5. Eligible evidence</h2>{claims_table(a.eligible_claims)}
<h2>6. Rejected evidence</h2>{claims_table(a.rejected_claims, rejected=True)}
<h2>7. Missing data</h2>{f"<ul>{missing}</ul>" if missing else "<p class='muted'>None.</p>"}
"""
    style = """body{font-family:system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#1b1f1d;line-height:1.45}
h1{font-size:22px}h2{font-size:17px;margin-top:28px;border-bottom:1px solid #ccd;padding-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:12.5px}td,th{border:1px solid #d5dad7;padding:5px 6px;vertical-align:top;text-align:left}
th{background:#eef2ef}.muted{color:#5d6660;font-size:13px}.badge{background:#fff3cd;color:#7a5b00;border-radius:4px;padding:0 4px;font-size:11px}
button{padding:6px 12px}@media print{button{display:none}}"""
    return f"<!doctype html><html><head><meta charset='utf-8'><title>Site assessment report</title>" \
           f"<style>{style}</style></head><body>{body}</body></html>"


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="static")
