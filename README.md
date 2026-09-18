# EcoIQ: Evidence-Constrained Environmental Reasoning System

Submission for the **Darukaa.Earth AI Biodiversity Intelligence Chatbot Challenge**.

> An evidence-constrained environmental reasoning system that diagnoses interacting ecological pressures and
> selects context-appropriate interventions, where an LLM is used only as a conversational interface and
> explanation layer, never as the source of scientific facts.

**Live demo:** `<VERCEL_URL>` · **API:** `<RENDER_URL>` · **Scope:** rainfed cropland, semi-arid to sub-humid agro-ecological zones, peninsular India.

```
.
├── backend/     FastAPI · Pydantic · deterministic reasoning engine · ChromaDB · pytest
│                deployed on Render (Python web service)
├── frontend/    React 18 · Vite · Tailwind CSS · Axios · Recharts · Web Speech API
│                deployed on Vercel (static build)
├── render.yaml  backend service definition
└── Dockerfile   optional single-container build (frontend + backend on one origin)
```

The two halves are independent: the frontend calls the API through `VITE_API_URL`, and the backend
allows that origin through `CORS_ORIGINS`. The Dockerfile remains for anyone who prefers to run both
from one process.

---

## 1. Where to look for each evaluation criterion

| Criterion | Open this | What it shows |
|---|---|---|
| Depth of reasoning (30 %) | **Diagnosis** tab, then **Action plan** | Limiting constraint vs top-ranked driver, causal pathways, and why agroforestry is deferred behind water conservation on demo site 1 |
| Scientific grounding (25 %) | **Evidence** tab → *Rejected* | Studies excluded by a load-bearing context mismatch, each with the reason; unverified claims are labelled, never hidden |
| Knowledge system design (20 %) | **Knowledge base** drawer, `GET /api/search`, README §5 | ChromaDB collections, semantic search, and the exact-filter vs similarity split |
| Conversational intelligence (15 %) | **Conversation** panel | Clarifying questions when data is missing, "sharpen this" prompts when it is not, multi-turn memory, and direct answers to "what about cover crops?" |
| Output clarity (10 %) | **Report & data** tab → *Open report* | Recommendation, impacted metrics, measurable target, time horizon, evidence and confidence in one printable document |

**On the brief's worked example** (semi-arid, 0.3 % SOC, monoculture wheat, low rainfall): that is demo site 1. EcoIQ does recommend diversification and agroforestry, but it **sequences water conservation first** and says why, because establishing new biomass competes for the scarce resource before it pays back. That ordering, not the list of interventions, is the non-obvious part.

## 2. What makes this different from a chatbot

| Property | How it is enforced |
|---|---|
| The LLM never produces a fact, number or recommendation | The LLM touches only two places, the **Extractor** (text → fields) and the **Narrator** (Assessment → prose). Everything between them is deterministic Python over the knowledge base. |
| Swapping or removing the model does not change the science | With `GEMINI_API_KEY` unset the system runs fully in deterministic mode and produces the same `Assessment`. |
| Every number in the prose is checkable | A **numeric and identifier guard** rejects LLM narration containing any number, claim id or identifier absent from the Assessment, then falls back to the template. Tested with corrupted narrations. |
| Evidence is filtered by context, not just retrieved | Claims carry `critical_dimensions`. A mismatch on one **disqualifies** the claim, a soft mismatch lowers its score, and rejected claims are **shown** in the UI. |
| No false certainty | Drivers are **ranked hypotheses**. When explanations are close, or the user's hypothesis ranks lower, the system names the measurement that would separate them. With critical data missing it **declines to recommend**. |
| Confidence is decomposed | Supporting claims, mean context match, data completeness and conflicts, each with its point contribution. |
| Recommendations are measurable | Every step carries a target computed from the thresholds table (e.g. soil moisture 13 % -> 25 %, FAO-56 field capacity for loam) plus any quantified effect size its evidence provides. |

## 3. Architecture

```
 user text ──► EXTRACTOR (Gemini JSON mode │ rule-based fallback) ──┐
 form / JSON input ────────────────────────────────────────────────┤  field_sources recorded per value
 stored site + dated measurements (ChromaDB) ──────────────────────┤
 lat/lon ──► zones collection (metadata range filter) ─────────────┘
                                   │
                          STATE BUILDER (SiteState)
                                   │ critical variable missing? ──► insufficient_data + templated clarifying questions
                                   ▼
 ┌──────────────── deterministic, no LLM (backend/app/reasoning, pure functions) ────────┐
 │ 1 suitability     thresholds → 0-1 per variable (Liebig-style limiting factor)        │
 │ 2 diagnosis       causal relationship graph → best path per driver → ranked drivers   │
 │ 3 temporal        measurements → trends → co-decline strengthens a hypothesis         │
 │ 4 retrieval       ChromaDB: claims where target_metric ∈ metrics on causal paths       │
 │ 5 context match   critical dimension mismatch ⇒ reject; else soft score               │
 │ 6 sequencing      relieve limiting constraint → act on drivers → defer water-competing │
 │ 7 warnings        magnitudes from non-matching contexts flagged as non-transferable   │
 │ 8 confidence      4-part breakdown                                                    │
 └───────────────────────────────────────────┬───────────────────────────────────────────┘
                                             ▼
               Assessment (Pydantic contract)  +  semantic mechanism passages (ChromaDB vector query)
                         ┌───────────────────┼─────────────────────┐
                         ▼                   ▼                     ▼
               NARRATOR (LLM rephrase   HTML report          React dashboard
               + numeric guard,         /api/report/{id}     (diagnosis, plan, evidence,
               template fallback)                            trends, raw JSON)
```

## 4. Reasoning engine walkthrough

**Suitability** (`backend/app/reasoning/suitability.py`). Each variable is scored 0-1 against a threshold row (numeric ramp, optimum band for pH, or enum scores). Every threshold cites a source or is explicitly marked `modelling_choice`.

**Limiting factor.** The lowest suitability among variables with a recorded causal pathway to the user's concern.

**Causal paths and ranking** (`diagnosis.py`). Conditional edges (e.g. `moisture_percent → ndvi_proxy`, semi-arid/sub-humid only) are searched for the highest weight-product path (depth ≤ 3) to the outcome. `rank = (1 − suitability) × path_support × trend_factor`, where `trend_factor` is 1.25 if the driver declined along with the outcome, 0.85 if stable and 0.6 if improving.

**Under-determination and hypotheses.** Top two supporting drivers within 20 % count as under-determined. A user's lower-ranked hypothesis is never dismissed. The system states what the evidence more strongly supports, that this does not rule the hypothesis out, and which measurement would discriminate.

**Context matching** (`context_match.py`). Dimensions are climate zone, rainfall range, soil texture and production system. A known mismatch on a critical dimension means **disqualified** with a reason. Other dimensions contribute a soft score, and unknown site values score 0.5 instead of disqualifying.

**Sequencing** (`selector.py`).
- **Stage 1:** interventions improving the limiting factor or its next pathway node.
- **Stage 2:** interventions on other ranked drivers.
- **Stage 3:** on water-limited sites, water-competing interventions (agroforestry, cover crops) are deferred with the reason stated.
- Interventions whose target pressure is absent or unobserved are not recommended. Adverse context-valid evidence is attached as a caveat.

## 5. Knowledge base (ChromaDB)

The curated source of truth is the set of CSV/JSON files in `backend/data/`. On startup `ChromaStore` loads them into a **persistent, embedded ChromaDB**, and re-seeds automatically when the files' fingerprint changes.

| Collection | Kind | Contents / how it is queried |
|---|---|---|
| `claims` | semantic | 37 intervention → metric claims. Exact retrieval via metadata filter `target_metric $in [...]`; similarity search powers `/api/search` |
| `relationships` | semantic | 25 conditional causal edges. Similarity search surfaces supporting mechanism passages per recommendation |
| `rec_sources` | record | 30 references (FAO, IPCC SRCCL, ICAR-CRIDA, ICRISAT, meta-analyses), with DOIs |
| `rec_thresholds` | record | Suitability cut-offs with source and note |
| `rec_interventions` | record | Sequencing properties: `competes_for_water`, `addresses_variable` |
| `rec_zones` | record | Agro-climatic boxes. `lat_min ≤ lat ≤ lat_max` metadata range query |
| `rec_sites`, `rec_measurements` | record | Demo sites and dated history (filtered by `site_id`) |
| `rec_conversations`, `rec_messages`, `rec_assessments` | record | Multi-turn state with per-field provenance; stored assessments for reports |
| `doc_chunks` | semantic | **Optional**: passages from source PDFs placed in `backend/data/sources/` and indexed with `python scripts/ingest_docs.py`. When present they replace the curated mechanisms as supporting passages, with source id and page number |

**Embeddings.** The default is an offline, deterministic embedding (feature-hashed stemmed unigrams and bigrams with an agronomy synonym map; `app/retrieval/embeddings.py`). It needs no model download, gives identical vectors everywhere and uses almost no memory. Set `EMBEDDING_MODEL=minilm` to use Chroma's all-MiniLM-L6-v2 instead.

**Semantic search never selects a recommendation.** It only retrieves context, and `tests/test_chroma_store.py` asserts ChromaDB and the in-memory store produce identical Assessments.

### Indexing source documents (optional)
```bash
cd backend
# name each PDF after its source id, e.g. data/sources/ipcc_srccl_2019.pdf
python scripts/ingest_docs.py
```
Chunks are ~1,200 characters with page numbers preserved, embedded with the same offline function. With no documents present, nothing changes: supporting passages fall back to the curated causal mechanisms.

### Verification status
Every claim starts `verified=false` with no page number, and **no page numbers or quotes were invented**. Four claims carry quantified effect sizes proposed from their cited sources and awaiting manual confirmation; the rest support a direction of change only, and the output says so rather than inventing a number. The UI shows an "unverified" badge, and confidence is reduced while supporting claims are unverified.

## 6. Modelling choices (stated, not hidden)
- Liebig's Law is adapted as a *limiting-constraint heuristic*, not a claim that biodiversity has a single cause.
- Enum scores and some numeric floors are `modelling_choice` rows: the ordering comes from the cited source, the exact numbers are ours.
- Relationship weights are curator judgements, not fitted coefficients.
- Constants: trend ±5 %, under-determination margin 20 %, water-limited cut-off 0.4, "pressure absent" cut-off 0.7.
- Zones are approximate boxes derived from the NBSS&LUP agro-ecological region map.

## 7. API

| Method | Path | |
|---|---|---|
| GET | `/api/health` | store backend, collection counts, LLM status |
| POST | `/api/chat` | `{message, conversation_id?, site_id?, site_json?}` → extraction, Assessment, narration, clarifying questions, `improvement_questions`, and `focus` answers when the message names an intervention |
| POST | `/api/assess` | Structured JSON input: `{site: SiteState, measurements?: [...]}` |
| GET | `/api/sites`, `/api/sites/{id}` | Demo sites + measurement history |
| POST | `/api/sites/{id}/assess` | Assess a stored site |
| GET | `/api/report/{assessment_id}` | Printable HTML report (browser print → PDF) |
| GET | `/api/knowledge/{claims,relationships,thresholds,interventions,sources}` | Full transparency |
| GET | `/api/search?q=&scope=claims\|docs` | ChromaDB semantic search over claim mechanisms or indexed source passages |
| GET | `/api/zone?lat=&lon=` | Climate-zone lookup |

## 8. Frontend

React 18 + Vite + Tailwind CSS + Axios (`frontend/src/lib/api.js`). One scrolling page: a full-screen
landing, how it works, the four worked examples, the input panel (free text **or** a guided form with a
JSON view), then the assessment, which unfolds as five sections with a sticky jump bar:
- **What's holding it back:** limiting-constraint gauge, hypothesis weighing, ranked drivers with pathways, suitability profile, confidence breakdown, and “sharpen this assessment” prompts.
- **What to do, in order:** staged timeline with rationale, a measurable target per metric, quantified effects where the evidence has them, and transfer warnings.
- **The evidence:** eligible vs rejected claims with reasons, filterable by metric.
- **History:** measurement trend charts.
- **Full write-up:** narration with guard status, input provenance, raw Assessment JSON, printable report.

A **Knowledge base** drawer offers semantic search and the source list.

**Voice** (`frontend/src/lib/speech.js`). The browser's Web Speech API gives speech-to-text for the chat
and text-to-speech for the answer: no extra service, no API key, nothing leaves the browser. A question
asked by voice is answered aloud automatically; typed questions get a **Listen** button. The spoken
summary is built from the same Assessment (`lib/spoken.js`), so voice introduces no new facts.

The frontend contains display labels only, no science.

## 9. Demo scenarios (asserted in `backend/tests/test_scenarios.py`)
1. **Beed: multi-stressor, sequenced.** The limiting factor is soil moisture, while the top biodiversity driver is habitat diversity. Water conservation goes first; agroforestry is deferred.
2. **Anantapur: user blames pesticides.** Habitat loss ranks higher, pesticides are explicitly not ruled out, and the answer names the discriminating measurement.
3. **Dharwad: transfer warning.** Cover-crop SOC magnitude is flagged as non-transferable; at 450 mm the claim is rejected outright.
4. **Unnamed plot: insufficient data.** No recommendation. Each missing variable is listed with what it would unlock, plus clarifying questions.

## 10. Local setup

Backend (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
python -m pytest -q                 # 49 tests, no network needed
uvicorn app.main:app --reload --port 8000
```
Frontend (Node 20+), in a second terminal:
```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173, proxies /api to :8000
```
Single-process alternative: `cd frontend && npm run build`, then run the backend, which serves
`frontend/dist` at http://localhost:8000. Docker: `docker compose up --build`.

Optional `backend/.env` (see `.env.example`): `GEMINI_API_KEY` enables LLM extraction and narration;
without it the system runs fully deterministically. Other settings: `CHROMA_PATH`, `EMBEDDING_MODEL`,
`STORE=csv` (in-memory store), `CORS_ORIGINS`. For the split deployment set `VITE_API_URL` in
`frontend/.env` (see `frontend/.env.example`).

Voice needs HTTPS or localhost. The microphone works in Chrome, Edge and Safari; Firefox can speak the
answer but not listen.

## 11. CI/CD

**GitHub Actions** (`.github/workflows/ci.yml`), on every push:
- `backend-tests`: pytest over the reasoning core, the four scenarios, ChromaDB/CSV parity, the LLM boundary and output quality (49 tests, no network needed).
- `frontend-build`: a production Vite build, so a broken frontend fails CI rather than the deploy.
- `keep-alive` (scheduled, every 3 days): pings `/api/health` so the free backend is warm for reviewers. Set the repo variable `APP_URL` to the Render URL.

**Backend on Render** (`render.yaml`): Python web service, root directory `backend`,
`pip install -r requirements.txt` then `uvicorn app.main:app`, health check `/api/health`.
Environment: `CORS_ORIGINS` (the Vercel origin), optional `GEMINI_API_KEY`, `EMBEDDING_MODEL`,
`CHROMA_PATH`. The free tier has no persistent disk, so ChromaDB re-seeds from `backend/data/` on boot
(a few seconds) and saved conversations reset on restart; the knowledge base and demos are unaffected.
Free instances sleep after ~15 minutes idle, so the first request can take up to a minute.

**Frontend on Vercel** (`frontend/vercel.json`): root directory `frontend`, Vite preset, one environment
variable `VITE_API_URL` pointing at the Render URL. Both deploy automatically on push to `main`.

## 12. Known limitations
- Small knowledge base (37 claims), verification in progress; see §5. Four claims carry quantified effect sizes; the rest support a direction of change only, and the output says so explicitly rather than inventing a number.
- Suitability is concern-agnostic (one threshold set).
- Zone lookup uses bounding boxes, not official polygons.
- The default embeddings are lexical-semantic (hashing and synonyms), not a neural model; MiniLM is one env var away.
