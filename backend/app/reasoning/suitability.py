"""Suitability scoring and limiting factor (CLAUDE.md 4.1). Pure functions.

Every cut-off comes from a Threshold row (with a source_id), never from this file.
Adapted from Liebig's Law of the Minimum: the system reports the lowest-scoring
variable as the limiting constraint, and also a geometric-mean index so the
"single scarcest factor" framing is never the only view (see README, "Modelling choices").
"""
from __future__ import annotations

import math

from app.models import SiteState, Threshold

UPPER_SUFFIX = ":upper"  # second threshold row for optimum-band variables (e.g. pH)


def _linear(value: float, poor: float, good: float) -> float:
    if poor == good:
        return 1.0 if value == good else 0.0
    return max(0.0, min(1.0, (value - poor) / (good - poor)))


def pick_threshold(thresholds: list[Threshold], variable: str, site: SiteState) -> Threshold | None:
    """Most specific row wins: exact zone+texture > zone or texture > wildcard."""
    best, best_rank = None, -1
    for t in thresholds:
        if t.variable != variable:
            continue
        if t.climate_zone not in ("*", site.climate_zone) or t.texture_class not in ("*", site.texture_class):
            continue
        rank = (t.climate_zone != "*") + (t.texture_class != "*")
        if rank > best_rank:
            best, best_rank = t, rank
    return best


def suitability(variable: str, value, site: SiteState, thresholds: list[Threshold]) -> float | None:
    """0-1 score for one variable, or None if no threshold applies or value unknown."""
    if value is None:
        return None
    t = pick_threshold(thresholds, variable, site)
    if t is None:
        return None
    if t.enum_scores:
        key = str(value).lower()
        return t.enum_scores.get(key)
    if t.poor is None or t.good is None:
        return None
    score = _linear(float(value), t.poor, t.good)
    upper = pick_threshold(thresholds, variable + UPPER_SUFFIX, site)
    if upper is not None and upper.poor is not None and upper.good is not None:
        score = min(score, _linear(float(value), upper.poor, upper.good))
    return round(score, 2)


def score_site(site: SiteState, thresholds: list[Threshold], exclude: set[str] = frozenset()) -> dict[str, float]:
    variables = {t.variable for t in thresholds if not t.variable.endswith(UPPER_SUFFIX)}
    scores = {}
    for var in sorted(variables - set(exclude)):
        s = suitability(var, getattr(site, var, None), site, thresholds)
        if s is not None:
            scores[var] = s
    return scores


def target_for(variable: str, site: SiteState, thresholds: list[Threshold]) -> tuple[float | str, str, str] | None:
    """(target value, source_id, note) that would score this variable as adequate."""
    t = pick_threshold(thresholds, variable, site)
    if t is None:
        return None
    if t.enum_scores:
        best = max(t.enum_scores.items(), key=lambda kv: (kv[1], kv[0]))
        return best[0], t.source_id, t.note
    if t.good is None:
        return None
    return t.good, t.source_id, t.note


def limiting_factor(scores: dict[str, float]) -> str | None:
    if not scores:
        return None
    # tie-break alphabetically so the result is deterministic
    return min(sorted(scores), key=lambda v: scores[v])


def geometric_index(scores: dict[str, float], floor: float = 0.01) -> float:
    if not scores:
        return 0.0
    return round(math.exp(sum(math.log(max(floor, s)) for s in scores.values()) / len(scores)), 2)
