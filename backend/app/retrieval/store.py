"""Knowledge store. Two interchangeable backends with identical behaviour:

- ChromaStore (chroma_store.py): persistent ChromaDB, semantic search over the knowledge base (default)
- CsvStore: loads data/*.csv into memory (tests, offline fallback)

The CSVs in data/ are the curated source of truth for both.

Every query here is a plain lookup. No ranking or judgement lives in this file.
"""
from __future__ import annotations

import csv
import json
import os
import re
import threading
import uuid
from pathlib import Path

from app.models import Claim, Intervention, Measurement, Relationship, SiteState, Source, Threshold

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# --------------------------------------------------------------------------- CSV parsing
def _list(v: str) -> list[str]:
    return [x.strip() for x in v.split("|") if x.strip()] if v else []


def _float(v: str) -> float | None:
    return float(v) if v not in ("", None) else None


def _int(v: str) -> int | None:
    return int(v) if v not in ("", None) else None


def _bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _enum_scores(v: str) -> dict[str, float]:
    out = {}
    for part in _list(v):
        k, s = part.split(":")
        out[k.strip()] = float(s)
    return out


def read_csv(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if any(r.values()) and not (r.get("id") or "").startswith("#")]


def parse_sources() -> list[Source]:
    return [Source(id=r["id"], title=r["title"], publisher=r["publisher"], year=int(r["year"]),
                   region=r["region"] or None, url=r["url"] or None) for r in read_csv("sources.csv")]


def parse_claims() -> list[Claim]:
    return [Claim(
        id=r["id"], intervention=r["intervention"], target_metric=r["target_metric"],
        direction=r["direction"], effect_min=_float(r["effect_min"]), effect_max=_float(r["effect_max"]),
        effect_unit=r["effect_unit"] or None, time_horizon=r["time_horizon"], mechanism=r["mechanism"],
        ctx_climate_zone=_list(r["ctx_climate_zone"]), ctx_rainfall_min=_float(r["ctx_rainfall_min"]),
        ctx_rainfall_max=_float(r["ctx_rainfall_max"]), ctx_soil_texture=_list(r["ctx_soil_texture"]),
        ctx_system=_list(r["ctx_system"]), critical_dimensions=_list(r["critical_dimensions"]),
        evidence_strength=r["evidence_strength"], source_id=r["source_id"], page=_int(r["page"]),
        quote=r["quote"] or None, verified=_bool(r["verified"]),
    ) for r in read_csv("claims.csv")]


def parse_relationships() -> list[Relationship]:
    return [Relationship(
        id=r["id"], from_variable=r["from_variable"], to_variable=r["to_variable"], weight=float(r["weight"]),
        ctx_climate_zone=_list(r["ctx_climate_zone"]), ctx_soil_texture=_list(r["ctx_soil_texture"]),
        mechanism=r["mechanism"], source_id=r["source_id"], verified=_bool(r["verified"]),
    ) for r in read_csv("relationships.csv")]


def parse_thresholds() -> list[Threshold]:
    return [Threshold(
        variable=r["variable"], climate_zone=r["climate_zone"] or "*", texture_class=r["texture_class"] or "*",
        poor=_float(r["poor"]), good=_float(r["good"]), enum_scores=_enum_scores(r["enum_scores"]),
        source_id=r["source_id"], note=r["note"],
    ) for r in read_csv("thresholds.csv")]


def parse_interventions() -> list[Intervention]:
    return [Intervention(id=r["id"], label=r["label"], category=r["category"],
                         competes_for_water=_bool(r["competes_for_water"]),
                         addresses_variable=r["addresses_variable"] or None, note=r["note"],
                         source_id=r["source_id"]) for r in read_csv("interventions.csv")]


def parse_zones() -> list[dict]:
    return [dict(r, lat_min=float(r["lat_min"]), lat_max=float(r["lat_max"]), lon_min=float(r["lon_min"]),
                 lon_max=float(r["lon_max"]), priority=int(r["priority"])) for r in read_csv("zones.csv")]


def load_demo_sites() -> list[dict]:
    return json.loads((DATA_DIR / "demo_sites.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- CSV store
class CsvStore:
    backend = "csv"

    def __init__(self):
        self._sources = {s.id: s for s in parse_sources()}
        self._claims = parse_claims()
        self._edges = parse_relationships()
        self._thresholds = parse_thresholds()
        self._interventions = {i.id: i for i in parse_interventions()}
        self._zones = parse_zones()
        self._sites: dict[str, dict] = {}
        self._measurements: dict[str, list[Measurement]] = {}
        for s in load_demo_sites():
            self._sites[s["state"]["site_id"]] = s
            self._measurements[s["state"]["site_id"]] = [
                Measurement(site_id=s["state"]["site_id"], **m) for m in s.get("measurements", [])]
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}
        self._assessments: dict[str, dict] = {}

    fallback_reason: str | None = None

    def ping(self) -> bool:
        return True

    def semantic_passages(self, query: str, k: int = 3) -> list[dict]:
        """Keyword fallback for mechanism-passage retrieval (ChromaStore uses embeddings)."""
        terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 3]
        scored = []
        for e in self._edges:
            hits = sum(e.mechanism.lower().count(t) for t in terms)
            if hits:
                scored.append((hits, e))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [{"id": e.id, "text": e.mechanism, "source_id": e.source_id, "score": float(h)}
                for h, e in scored[:k]]

    def sources(self) -> list[Source]:
        return list(self._sources.values())

    def source_titles(self) -> dict[str, str]:
        return {k: v.title for k, v in self._sources.items()}

    def all_claims(self) -> list[Claim]:
        return list(self._claims)

    def claims_for_metrics(self, metrics: list[str]) -> list[Claim]:
        return [c for c in self._claims if c.target_metric in metrics]

    def relationships(self) -> list[Relationship]:
        return list(self._edges)

    def thresholds(self) -> list[Threshold]:
        return list(self._thresholds)

    def interventions(self) -> dict[str, Intervention]:
        return dict(self._interventions)

    def zone_for(self, lat: float, lon: float) -> str | None:
        hits = [z for z in self._zones if z["lat_min"] <= lat <= z["lat_max"] and z["lon_min"] <= lon <= z["lon_max"]]
        hits.sort(key=lambda z: z["priority"])
        return hits[0]["climate_zone"] if hits else None

    def search(self, q: str, limit: int = 10) -> list[dict]:
        terms = [t for t in re.findall(r"\w+", q.lower()) if len(t) > 2]
        scored = []
        for c in self._claims:
            text = f"{c.intervention} {c.target_metric} {c.mechanism}".lower()
            hits = sum(text.count(t) for t in terms)
            if hits:
                scored.append((hits, c))
        scored.sort(key=lambda x: -x[0])
        return [{"claim_id": c.id, "intervention": c.intervention, "target_metric": c.target_metric,
                 "mechanism": c.mechanism, "source_id": c.source_id, "rank": h} for h, c in scored[:limit]]

    def list_sites(self) -> list[dict]:
        return [{"site_id": k, "name": v["state"].get("name"), "demo_purpose": v.get("demo_purpose"),
                 "example_message": v.get("example_message")} for k, v in self._sites.items()]

    def get_site(self, site_id: str) -> SiteState | None:
        s = self._sites.get(site_id)
        return SiteState(**s["state"]) if s else None

    def measurements(self, site_id: str) -> list[Measurement]:
        return list(self._measurements.get(site_id, []))

    def get_conversation(self, cid: str) -> dict | None:
        c = self._conversations.get(cid)
        return None if c is None else {"id": cid, "site_state": c, "messages": self._messages.get(cid, [])}

    def save_conversation(self, cid: str, state: dict) -> None:
        self._conversations[cid] = state

    def add_message(self, cid: str, role: str, content: str, assessment_id: str | None = None) -> None:
        self._messages.setdefault(cid, []).append({"role": role, "content": content, "assessment_id": assessment_id})

    def save_assessment(self, site_id: str, input_state: dict, output: dict, narration: str) -> str:
        aid = uuid.uuid4().hex[:12]
        self._assessments[aid] = {"id": aid, "site_id": site_id, "input": input_state, "output": output,
                                  "narration": narration}
        return aid

    def get_assessment(self, aid: str) -> dict | None:
        return self._assessments.get(aid)


_store = None
_store_lock = threading.Lock()


def get_store():
    """ChromaDB (persistent, embedded) by default; STORE=csv or a Chroma failure falls back to memory."""
    global _store
    if _store is not None:
        return _store
    with _store_lock:  # concurrent first requests must not open two PersistentClients
        if _store is not None:
            return _store
        if os.getenv("STORE", "chroma").lower() == "csv":
            _store = CsvStore()
        else:
            try:
                from app.retrieval.chroma_store import ChromaStore
                _store = ChromaStore()
            except Exception as e:  # noqa: BLE001 - keep the app usable, report the reason in /api/health
                print(f"[store] ChromaDB unavailable, using in-memory CSV store: {e!r}")
                _store = CsvStore()
                _store.fallback_reason = repr(e)
    return _store
