"""Narrator: Assessment -> prose (CLAUDE.md 5.3) plus the mandatory numeric guard (5.4).

The template narration is complete on its own. The LLM may only rephrase it; the
guard rejects any rephrasing that introduces a number or identifier that is not in
the Assessment, and the template is used instead.
"""
from __future__ import annotations

import json
import re

from app.llm import LLMError, LLMService
from app.models import Assessment

STAGE_LABEL = {
    "relieve_limiting_constraint": "First: relieve the limiting constraint",
    "act_on_ranked_drivers": "Then: act on the ranked drivers",
    "defer_until_water_constraint_relieved": "Later: deferred until the water constraint is relieved",
}


def _fmt(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:g}"


def template_narration(a: Assessment) -> str:
    L: list[str] = []
    if a.status == "insufficient_data":
        L.append("**I can't give a responsible recommendation yet.** Some critical variables are missing, "
                 "and guessing them would make any advice unreliable.")
        L.append("")
        L.append("**What is missing and why it matters:**")
        for v in a.missing_variables:
            L.append(f"- `{v}`: {a.missing_variable_impact.get(v, '')}")
        return "\n".join(L)

    L.append(f"**Limiting constraint:** `{a.limiting_factor}` (suitability "
             f"{_fmt(a.suitability.get(a.limiting_factor))}), the scarcest factor among those with a recorded "
             f"pathway to your concern.")
    if a.drivers_ranked:
        L.append("")
        L.append("**Ranked explanations** (these are ranked hypotheses, not verdicts):")
        for d in a.drivers_ranked[:4]:
            trend = f", trend {d.temporal_trend}" if d.temporal_trend else ""
            L.append(f"- `{d.variable}`: suitability {_fmt(d.suitability_score)}, rank score {_fmt(d.rank_score)}"
                     f"{trend}; pathway {' -> '.join(d.path)} ({', '.join(d.source_ids)})")
    if a.hypothesis_note:
        L += ["", f"**On your hypothesis:** {a.hypothesis_note}"]
    if a.under_determined:
        L += ["", "**The data cannot yet separate the top two explanations.**"]
    if a.discriminating_measurement:
        L += ["", f"**What would settle it:** {a.discriminating_measurement}"]

    if a.sequence_detail:
        L += ["", "**Recommended sequence:**"]
        current = None
        for s in a.sequence_detail:
            if s.stage != current:
                current = s.stage
                L.append(f"*{STAGE_LABEL.get(s.stage, s.stage)}*")
            L.append(f"- `{s.intervention}` ({s.time_horizon}-term; improves {', '.join(s.target_metrics)}; "
                     f"evidence {', '.join(s.claim_ids)}). {s.rationale}")
            for t in s.metric_targets:
                unit = f" {t.unit}" if t.unit else ""
                current = "not measured" if t.current is None else f"{_fmt(t.current) if isinstance(t.current, (int, float)) else t.current}{unit}"
                target = f"{_fmt(t.target) if isinstance(t.target, (int, float)) else t.target}{unit}"
                L.append(f"    - Target for `{t.variable}`: {current} -> {target} ({t.source_id})")
            for e in s.evidence_effects:
                flag = "" if e.verified else ", not yet source-verified"
                L.append(f"    - Reported effect ({e.claim_id}): {_fmt(e.effect_min)}-{_fmt(e.effect_max)} "
                         f"{e.effect_unit} over the {e.time_horizon} term, context match "
                         f"{_fmt(e.context_match_score)}{flag}")
            if not s.evidence_effects:
                L.append("    - No quantified effect size is available for this intervention in this context; "
                         "the direction of the effect is what the evidence supports.")
    if a.transfer_warnings:
        L += ["", "**Evidence transfer warnings:**"] + [f"- {w}" for w in a.transfer_warnings]
    if a.rejected_claims:
        L += ["", f"**Evidence excluded:** {len(a.rejected_claims)} claim(s) were rejected because a load-bearing "
                  f"context did not match this site:"]
        L += [f"- {c.claim_id} ({c.intervention} -> {c.target_metric}): {c.disqualify_reason}" for c in a.rejected_claims]
    c = a.confidence
    L += ["", f"**Confidence: {c.level}** ({'; '.join(c.rationale)})"]
    return "\n".join(L)


# --------------------------------------------------------------------------- guard
NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")
IDENT_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
CLAIM_ID_RE = re.compile(r"\b[CR]\d{2}\b")


def _norm(n: str) -> str:
    n = n.replace(",", "")
    try:
        return f"{float(n):g}"
    except ValueError:
        return n


def numeric_guard(narration: str, a: Assessment, template: str) -> dict:
    """Every number and identifier in the narration must already exist in the Assessment or template."""
    source = json.dumps(a.model_dump(), default=str) + "\n" + template
    allowed_nums = {_norm(x) for x in NUMBER_RE.findall(source)}
    allowed_idents = set(IDENT_RE.findall(source)) | set(CLAIM_ID_RE.findall(source))
    bad_nums = sorted({x for x in NUMBER_RE.findall(narration) if _norm(x) not in allowed_nums})
    bad_idents = sorted({x for x in IDENT_RE.findall(narration) + CLAIM_ID_RE.findall(narration)
                         if x not in allowed_idents})
    return {"passed": not bad_nums and not bad_idents, "unsupported_numbers": bad_nums,
            "unsupported_identifiers": bad_idents}


NARRATE_SYSTEM = """You rewrite a computed environmental assessment into clear, readable prose for a farmer or field scientist.
Hard rules:
- Use ONLY facts in the provided text. Do not add any number, percentage, date, source, study, intervention or recommendation.
- Copy every number exactly as written. Do not round, convert units or compute new numbers.
- Keep snake_case identifiers (like `moisture_percent`, `residue_retention`) and claim ids (like C14) verbatim when you mention them.
- Keep the order of the recommended sequence and keep every warning and the confidence rationale.
- Do not use numbered lists; use short paragraphs and bullet points.
- Present explanations as ranked hypotheses, never as certain causes."""


def narrate(a: Assessment, llm: LLMService, max_attempts: int = 2) -> dict:
    template = template_narration(a)
    if not llm.enabled:
        return {"text": template, "mode": "template", "guard": None}
    reports = []
    for _ in range(max_attempts):
        try:
            text = llm.generate_text(NARRATE_SYSTEM, template)
        except LLMError as e:
            reports.append({"passed": False, "error": str(e)})
            break
        report = numeric_guard(text, a, template)
        reports.append(report)
        if report["passed"]:
            return {"text": text, "mode": "llm", "guard": reports}
    return {"text": template, "mode": "template_fallback", "guard": reports}
