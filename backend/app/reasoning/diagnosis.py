"""Diagnosis: causal-path search, hypothesis ranking, under-determination (CLAUDE.md 4.2-4.3).

Pure functions. Never emits "X is the cause"; it ranks explanations and, when the
data cannot separate the top two, names the measurement that would.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Driver, Measurement, Relationship, SiteState, Threshold
from app.reasoning.suitability import limiting_factor, pick_threshold, score_site
from app.reasoning.temporal import trend_factor, trends_by_variable

# Which observed variable operationalises each user concern. Definitional, not scientific.
CONCERN_OUTCOME = {
    "biodiversity_decline": "species_richness_index",
    "pollinator_decline": "pollinator_observed",
    "soil_degradation": "soc_percent",
    "vegetation_decline": "ndvi_proxy",
}
DEFAULT_CONCERN = "biodiversity_decline"

MAX_PATH_DEPTH = 3
UNDERDETERMINED_MARGIN = 0.2   # top two within 20% of the top score -> under-determined
CONCERN_SUITABILITY_CUTOFF = 0.7


@dataclass
class DiagnosisResult:
    outcome_variable: str
    suitability: dict[str, float]
    limiting_factor: str | None
    drivers: list[Driver]
    under_determined: bool
    discriminating_measurement: str | None
    hypothesis_note: str | None
    trends: dict[str, str] = field(default_factory=dict)


def edge_applies(edge: Relationship, site: SiteState) -> bool:
    """Unknown site context does not block an edge; a known mismatch does."""
    if edge.ctx_climate_zone and site.climate_zone and site.climate_zone not in edge.ctx_climate_zone:
        return False
    if edge.ctx_soil_texture and site.texture_class and site.texture_class not in edge.ctx_soil_texture:
        return False
    return True


def best_path(start: str, goal: str, edges: list[Relationship], site: SiteState,
              max_depth: int = MAX_PATH_DEPTH) -> tuple[float, list[Relationship]]:
    """Highest weight-product path start -> goal. Returns (0, []) if none."""
    usable = [e for e in edges if edge_applies(e, site)]
    best: tuple[float, list[Relationship]] = (0.0, [])

    def walk(node: str, support: float, trail: list[Relationship], seen: set[str]):
        nonlocal best
        if node == goal and trail:
            if support > best[0]:
                best = (support, list(trail))
            return
        if len(trail) >= max_depth:
            return
        for e in usable:
            if e.from_variable == node and e.to_variable not in seen:
                trail.append(e)
                walk(e.to_variable, support * e.weight, trail, seen | {e.to_variable})
                trail.pop()

    walk(start, 1.0, [], {start})
    return round(best[0], 3), best[1]


def _worsening_trend(var: str, raw: str | None, site: SiteState, thresholds: list[Threshold]) -> str | None:
    """Translate a numeric trend into ecological direction (rising temperature is 'declining' condition)."""
    if raw in (None, "stable"):
        return raw
    t = pick_threshold(thresholds, var, site)
    if t and t.poor is not None and t.good is not None and t.good < t.poor:
        return {"declining": "improving", "improving": "declining"}[raw]
    return raw


def rank_drivers(site: SiteState, edges: list[Relationship], thresholds: list[Threshold],
                 measurements: list[Measurement], concern: str) -> DiagnosisResult:
    outcome = CONCERN_OUTCOME.get(concern, CONCERN_OUTCOME[DEFAULT_CONCERN])
    scores = score_site(site, thresholds, exclude={outcome})
    raw_trends = trends_by_variable(measurements)
    trends = {v: _worsening_trend(v, t, site, thresholds) for v, t in raw_trends.items()}
    outcome_trend = trends.get(outcome)

    drivers: list[Driver] = []
    for var, s in scores.items():
        support, path = best_path(var, outcome, edges, site)
        if support == 0:
            continue
        tf = trend_factor(trends.get(var), outcome_trend)
        rank = round((1 - s) * support * tf, 3)
        nodes = [var] + [e.to_variable for e in path]
        mech = "; then ".join(f"{e.from_variable} -> {e.to_variable}: {e.mechanism}" for e in path)
        drivers.append(Driver(
            variable=var,
            suitability_score=s,
            supports_concern=s < CONCERN_SUITABILITY_CUTOFF and tf >= 0.85,
            temporal_trend=trends.get(var),
            assumption=f"Assumes the pathway {' -> '.join(nodes)} operates at this site. {mech}",
            path_support=support,
            rank_score=rank,
            path=nodes,
            source_ids=sorted({e.source_id for e in path}),
        ))
    drivers.sort(key=lambda d: (-d.rank_score, d.variable))

    supporting = [d for d in drivers if d.supports_concern]
    under = False
    disc = None
    if len(supporting) >= 2 and supporting[0].rank_score > 0:
        r1, r2 = supporting[0].rank_score, supporting[1].rank_score
        if (r1 - r2) / r1 < UNDERDETERMINED_MARGIN:
            under = True
            disc = discriminating_measurement(supporting[0], supporting[1], site, outcome, trends)

    note = None
    hyp = site.user_hypothesis
    if hyp and drivers:
        top = supporting[0] if supporting else drivers[0]
        hyp_driver = next((d for d in drivers if d.variable == hyp), None)
        if hyp == top.variable:
            note = (f"The current evidence is consistent with your hypothesis: {hyp} is the "
                    f"highest-ranked explanation for {outcome}.")
        elif not site.known(hyp):
            note = (f"{hyp} has not been measured for this site, so your hypothesis cannot be ranked yet. "
                    f"The current evidence most strongly supports {top.variable}.")
            disc = disc or f"Measure {hyp}: it is required to rank your hypothesis against {top.variable}."
        elif hyp_driver is None:
            note = (f"No causal pathway from {hyp} to {outcome} is recorded for this site's context, "
                    f"so the current evidence does not support it as a driver; it more strongly supports "
                    f"{top.variable}. This does not rule {hyp} out, it means the knowledge base holds no "
                    f"evidence for that pathway under these conditions.")
        else:
            note = (f"The current evidence more strongly supports {top.variable} (rank score "
                    f"{top.rank_score}) than your hypothesis {hyp} (rank score {hyp_driver.rank_score}). "
                    f"This does not rule {hyp} out.")
            disc = disc or discriminating_measurement(top, hyp_driver, site, outcome, trends)

    return DiagnosisResult(
        outcome_variable=outcome,
        suitability=scores,
        # Liebig min over variables with a recorded pathway to the concern; a scarce factor
        # with no link to the outcome cannot be what limits it. Falls back to all scores.
        limiting_factor=limiting_factor({d.variable: d.suitability_score for d in drivers} or scores),
        drivers=drivers,
        under_determined=under,
        discriminating_measurement=disc,
        hypothesis_note=note,
        trends=trends,
    )


def discriminating_measurement(a: Driver, b: Driver, site: SiteState, outcome: str,
                               trends: dict[str, str]) -> str:
    """The additional observation that would separate hypothesis a from hypothesis b."""
    only_a = [v for v in a.path[1:] if v not in b.path and v != outcome]
    only_b = [v for v in b.path[1:] if v not in a.path and v != outcome]
    for var, mine, other in [(v, a, b) for v in only_a] + [(v, b, a) for v in only_b]:
        if not site.known(var):
            return (f"Measure {var}. It lies on the {mine.variable} pathway "
                    f"({' -> '.join(mine.path)}) but not on the {other.variable} pathway. "
                    f"If {var} is degraded, {mine.variable} is supported; if it is healthy, "
                    f"{other.variable} becomes the stronger explanation.")
    missing_history = [d.variable for d in (a, b) if d.variable not in trends]
    if missing_history or outcome not in trends:
        need = ", ".join(sorted(set(missing_history + ([outcome] if outcome not in trends else []))))
        return (f"Collect at least two dated observations of {need}. The driver whose decline "
                f"precedes or tracks the decline in {outcome} is the better-supported explanation "
                f"(temporal co-trend test).")
    return (f"Both {a.variable} and {b.variable} have trend data that fits the decline in {outcome}. "
            f"A paired comparison against a nearby reference plot differing only in {a.variable} "
            f"would separate the two explanations.")
