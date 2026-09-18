"""ChromaDB knowledge store (embedded, persistent).

Two kinds of collection:
- Semantic collections (`claims`, `relationships`): documents are embedded (MiniLM or, by
  default: offline hashing embeddings, see embeddings.py) so mechanism text can be searched by meaning.
- Record collections (everything else): rows stored as JSON documents with filterable metadata
  and a constant placeholder embedding. They are looked up by id or metadata `where` filters,
  never by similarity.

Retrieval for reasoning is still exact: claims are fetched with a metadata filter on
`target_metric`, and zones with numeric range filters. Similarity search is only used to surface
supporting mechanism passages and for /api/search. It never selects a recommendation.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

import chromadb

from app.retrieval.embeddings import get_embedding_function

from app.models import Claim, Intervention, Measurement, Relationship, SiteState, Source, Threshold
from app.retrieval.store import (DATA_DIR, load_demo_sites, parse_claims, parse_interventions,
                                 parse_relationships, parse_sources, parse_thresholds, parse_zones)

CHROMA_PATH = os.getenv("CHROMA_PATH", str(Path(__file__).resolve().parents[2] / "chroma_data"))
PLACEHOLDER = [1.0]
# doc_chunks is deliberately NOT reseeded from data/: indexed documents persist until --clear.
KNOWLEDGE_COLLECTIONS = ["claims", "relationships", "sources", "thresholds", "interventions", "zones", "sites",
                         "measurements"]
DATA_FILES = ["claims.csv", "relationships.csv", "sources.csv", "thresholds.csv", "interventions.csv",
              "zones.csv", "demo_sites.json"]


def _data_fingerprint() -> str:
    h = hashlib.sha256()
    for name in DATA_FILES:
        h.update((DATA_DIR / name).read_bytes())
    return h.hexdigest()[:16]


class ChromaStore:
    backend = "chroma"
    fallback_reason = None

    def __init__(self, path: str = CHROMA_PATH):
        self.client = chromadb.PersistentClient(path=path)
        self._ef = get_embedding_function()
        self._semantic = {name: self.client.get_or_create_collection(
            name, metadata={"hnsw:space": "cosine"}, embedding_function=self._ef)
                          for name in ("claims", "relationships", "doc_chunks")}
        self._records = {name: self._record_collection(name)
                         for name in KNOWLEDGE_COLLECTIONS + ["conversations", "messages", "assessments", "meta"]
                         if name not in self._semantic}
        self.seed_if_changed()

    # ------------------------------------------------------------------ setup
    def _record_collection(self, name: str):
        return self.client.get_or_create_collection(f"rec_{name}", embedding_function=None)

    def _col(self, name: str):
        return self._semantic[name] if name in self._semantic else self._records[name]

    def _put(self, name: str, ids: list[str], rows: list[dict], metadatas: list[dict] | None = None):
        if not ids:
            return
        metadatas = metadatas or [{"_": 0} for _ in ids]
        self._records[name].upsert(ids=ids, documents=[json.dumps(r, default=str) for r in rows],
                                   metadatas=metadatas, embeddings=[PLACEHOLDER] * len(ids))

    def seed_if_changed(self) -> None:
        """(Re)load the knowledge base from data/ when the CSV fingerprint changes."""
        fp = _data_fingerprint()
        meta = self._records["meta"].get(ids=["fingerprint"])
        if meta["documents"] and meta["documents"][0] == fp:
            return
        for name in KNOWLEDGE_COLLECTIONS:
            col_name = name if name in self._semantic else f"rec_{name}"
            self.client.delete_collection(col_name)
        self._semantic.update({name: self.client.get_or_create_collection(
            name, metadata={"hnsw:space": "cosine"}, embedding_function=self._ef)
            for name in ("claims", "relationships")})
        for name in KNOWLEDGE_COLLECTIONS:
            if name not in self._semantic:
                self._records[name] = self._record_collection(name)

        claims = parse_claims()
        self._semantic["claims"].add(
            ids=[c.id for c in claims],
            documents=[f"{c.intervention.replace('_', ' ')} affects {c.target_metric.replace('_', ' ')}: "
                       f"{c.mechanism}" for c in claims],
            metadatas=[{"target_metric": c.target_metric, "intervention": c.intervention, "source_id": c.source_id,
                        "payload": c.model_dump_json()} for c in claims])
        edges = parse_relationships()
        self._semantic["relationships"].add(
            ids=[e.id for e in edges],
            documents=[f"{e.from_variable.replace('_', ' ')} influences {e.to_variable.replace('_', ' ')}: "
                       f"{e.mechanism}" for e in edges],
            metadatas=[{"from_variable": e.from_variable, "to_variable": e.to_variable, "source_id": e.source_id,
                        "payload": e.model_dump_json()} for e in edges])

        sources = parse_sources()
        self._put("sources", [s.id for s in sources], [s.model_dump() for s in sources])
        th = parse_thresholds()
        self._put("thresholds", [f"{t.variable}|{t.climate_zone}|{t.texture_class}" for t in th],
                  [t.model_dump() for t in th], [{"variable": t.variable} for t in th])
        iv = parse_interventions()
        self._put("interventions", [i.id for i in iv], [i.model_dump() for i in iv])
        zones = parse_zones()
        self._put("zones", [z["id"] for z in zones], zones,
                  [{k: z[k] for k in ("lat_min", "lat_max", "lon_min", "lon_max", "priority")} | {
                      "climate_zone": z["climate_zone"]} for z in zones])
        sites = load_demo_sites()
        self._put("sites", [s["state"]["site_id"] for s in sites], sites)
        ms = [dict(m, site_id=s["state"]["site_id"]) for s in sites for m in s.get("measurements", [])]
        self._put("measurements", [f"{m['site_id']}|{m['variable']}|{m['date']}" for m in ms], ms,
                  [{"site_id": m["site_id"], "variable": m["variable"]} for m in ms])
        self._records["meta"].upsert(ids=["fingerprint"], documents=[fp], metadatas=[{"_": 0}],
                                     embeddings=[PLACEHOLDER])

    # ------------------------------------------------------------------ helpers
    def _all(self, name: str, where: dict | None = None) -> list[dict]:
        res = self._records[name].get(where=where) if where else self._records[name].get()
        return [json.loads(d) for d in res["documents"]]

    def counts(self) -> dict[str, int]:
        out = {n: self._col(n).count() for n in KNOWLEDGE_COLLECTIONS}
        out["doc_chunks"] = self.doc_chunk_count()
        return out

    # ------------------------------------------------------------------ knowledge
    def ping(self) -> bool:
        return self._semantic["claims"].count() > 0

    def sources(self) -> list[Source]:
        return sorted((Source(**r) for r in self._all("sources")), key=lambda s: s.id)

    def source_titles(self) -> dict[str, str]:
        return {s.id: s.title for s in self.sources()}

    def _claims(self, where: dict | None = None) -> list[Claim]:
        res = self._semantic["claims"].get(where=where, include=["metadatas"]) if where else \
            self._semantic["claims"].get(include=["metadatas"])
        return sorted((Claim.model_validate_json(m["payload"]) for m in res["metadatas"]), key=lambda c: c.id)

    def all_claims(self) -> list[Claim]:
        return self._claims()

    def claims_for_metrics(self, metrics: list[str]) -> list[Claim]:
        if not metrics:
            return []
        return self._claims({"target_metric": {"$in": list(metrics)}})

    def relationships(self) -> list[Relationship]:
        res = self._semantic["relationships"].get(include=["metadatas"])
        return sorted((Relationship.model_validate_json(m["payload"]) for m in res["metadatas"]), key=lambda e: e.id)

    def thresholds(self) -> list[Threshold]:
        return sorted((Threshold(**r) for r in self._all("thresholds")), key=lambda t: (t.variable, t.climate_zone,
                                                                                        t.texture_class))

    def interventions(self) -> dict[str, Intervention]:
        return {r["id"]: Intervention(**r) for r in self._all("interventions")}

    def zone_for(self, lat: float, lon: float) -> str | None:
        hits = self._all("zones", {"$and": [{"lat_min": {"$lte": lat}}, {"lat_max": {"$gte": lat}},
                                            {"lon_min": {"$lte": lon}}, {"lon_max": {"$gte": lon}}]})
        hits.sort(key=lambda z: z["priority"])
        return hits[0]["climate_zone"] if hits else None

    def _query(self, name: str, text: str, k: int) -> dict:
        col = self._semantic[name]
        return col.query(query_texts=[text], n_results=min(k, col.count()), include=["documents", "metadatas",
                                                                                     "distances"])

    def search(self, q: str, limit: int = 10) -> list[dict]:
        res = self._query("claims", q, limit)
        out = []
        for cid, meta, dist in zip(res["ids"][0], res["metadatas"][0], res["distances"][0]):
            c = Claim.model_validate_json(meta["payload"])
            out.append({"claim_id": cid, "intervention": c.intervention, "target_metric": c.target_metric,
                        "mechanism": c.mechanism, "source_id": c.source_id, "rank": round(1 - dist, 3)})
        return out

    # ------------------------------------------------------------------ source documents (optional)
    def doc_chunk_count(self) -> int:
        return self._semantic["doc_chunks"].count()

    def clear_docs(self) -> None:
        self.client.delete_collection("doc_chunks")
        self._semantic["doc_chunks"] = self.client.get_or_create_collection(
            "doc_chunks", metadata={"hnsw:space": "cosine"}, embedding_function=self._ef)

    def add_doc_chunks(self, source_id: str, chunks: list[tuple[int, str]]) -> None:
        self._semantic["doc_chunks"].upsert(
            ids=[f"{source_id}#p{page}#{i}" for i, (page, _) in enumerate(chunks)],
            documents=[text for _, text in chunks],
            metadatas=[{"source_id": source_id, "page": page} for page, _ in chunks])

    def search_docs(self, query: str, k: int = 5) -> list[dict]:
        if not self.doc_chunk_count():
            return []
        res = self._query("doc_chunks", query, k)
        return [{"id": i, "text": doc, "source_id": m["source_id"], "page": m["page"],
                 "score": round(1 - d, 3)}
                for i, doc, m, d in zip(res["ids"][0], res["documents"][0], res["metadatas"][0],
                                        res["distances"][0])]

    def semantic_passages(self, query: str, k: int = 3) -> list[dict]:
        """Prefer real source-document passages when any are indexed; otherwise use the curated
        relationship mechanisms, so the system behaves identically with no PDFs present."""
        docs = self.search_docs(query, k)
        if docs:
            return docs
        res = self._query("relationships", query, k)
        return [{"id": i, "text": Relationship.model_validate_json(m["payload"]).mechanism,
                 "source_id": m["source_id"], "score": round(1 - d, 3)}
                for i, m, d in zip(res["ids"][0], res["metadatas"][0], res["distances"][0])]

    # ------------------------------------------------------------------ sites
    def list_sites(self) -> list[dict]:
        return [{"site_id": s["state"]["site_id"], "name": s["state"].get("name"),
                 "demo_purpose": s.get("demo_purpose"), "example_message": s.get("example_message")}
                for s in sorted(self._all("sites"), key=lambda s: s["state"]["site_id"])]

    def get_site(self, site_id: str) -> SiteState | None:
        res = self._records["sites"].get(ids=[site_id])
        return SiteState(**json.loads(res["documents"][0])["state"]) if res["documents"] else None

    def measurements(self, site_id: str) -> list[Measurement]:
        rows = self._all("measurements", {"site_id": site_id})
        return sorted((Measurement(**r) for r in rows), key=lambda m: (m.variable, m.date))

    # ------------------------------------------------------------------ conversations / assessments
    def get_conversation(self, cid: str) -> dict | None:
        res = self._records["conversations"].get(ids=[cid])
        if not res["documents"]:
            return None
        msgs = self._records["messages"].get(where={"conversation_id": cid})
        rows = sorted((json.loads(d) for d in msgs["documents"]), key=lambda m: m["seq"])
        return {"id": cid, "site_state": json.loads(res["documents"][0]), "messages": rows}

    def save_conversation(self, cid: str, state: dict) -> None:
        self._put("conversations", [cid], [state])

    def add_message(self, cid: str, role: str, content: str, assessment_id: str | None = None) -> None:
        seq = self._records["messages"].count()
        self._put("messages", [uuid.uuid4().hex], [{"role": role, "content": content, "assessment_id": assessment_id,
                                                    "seq": seq}], [{"conversation_id": cid}])

    def save_assessment(self, site_id: str, input_state: dict, output: dict, narration: str) -> str:
        aid = uuid.uuid4().hex[:12]
        self._put("assessments", [aid], [{"id": aid, "site_id": site_id, "input": input_state, "output": output,
                                          "narration": narration}], [{"site_id": site_id}])
        return aid

    def get_assessment(self, aid: str) -> dict | None:
        res = self._records["assessments"].get(ids=[aid])
        return json.loads(res["documents"][0]) if res["documents"] else None
