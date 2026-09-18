"""Decomposed confidence (CLAUDE.md 4.8) and missing-data handling. Pure functions."""
from __future__ import annotations

from app.models import CRITICAL_VARIABLES, Claim, ClaimMatch, ConfidenceBreakdown, Relationship, SiteState


def conflicts(claims: list[ClaimMatch]) -> list[tuple[str, str]]:
    """(intervention, metric) pairs where context-valid claims point in opposite directions."""
    dirs: dict[tuple[str, str], set[str]] = {}
    for c in claims:
        dirs.setdefault((c.intervention, c.target_metric), set()).add(c.direction)
    return sorted(k for k, v in dirs.items() if len(v) > 1)


def confidence(used: list[ClaimMatch], all_eligible: list[ClaimMatch], site: SiteState,
               scoring_variables: list[str], under_determined: bool) -> ConfidenceBreakdown:
    n = len({c.claim_id for c in used})
    cq = round(sum(c.context_match_score for c in used) / len(used), 2) if used else 0.0
    known = sum(1 for v in scoring_variables if site.known(v))
    completeness = round(known / len(scoring_variables), 2) if scoring_variables else 0.0
    n_conf = len(conflicts(all_eligible))
    n_unverified = sum(1 for c in used if not c.verified)

    points = 0.0
    why = []
    if n >= 8:
        points += 2; why.append(f"{n} supporting claims (+2)")
    elif n >= 4:
        points += 1; why.append(f"{n} supporting claims (+1)")
    else:
        why.append(f"only {n} supporting claims (+0)")
    if cq >= 0.75:
        points += 1; why.append(f"mean context match {cq} (+1)")
    else:
        why.append(f"mean context match {cq} (+0)")
    if completeness >= 0.8:
        points += 1; why.append(f"data completeness {completeness} (+1)")
    elif completeness >= 0.6:
        points += 0.5; why.append(f"data completeness {completeness} (+0.5)")
    else:
        why.append(f"data completeness {completeness} (+0)")
    if n_conf:
        points -= min(2, n_conf); why.append(f"{n_conf} conflicting claim pair(s) (-{min(2, n_conf)})")
    if under_determined:
        points -= 1; why.append("top explanations are under-determined (-1)")
    if n and n_unverified / n > 0.5:
        points -= 0.5; why.append(f"{n_unverified} of {n} supporting claims not yet manually verified (-0.5)")

    level = "high" if points >= 4 else "moderate" if points >= 2 else "low"
    return ConfidenceBreakdown(level=level, n_supporting_claims=n, context_quality_mean=cq,
                               data_completeness=completeness, n_conflicts=n_conf, rationale=why)


def missing_critical(site: SiteState) -> list[str]:
    return [v for v in CRITICAL_VARIABLES if not site.known(v)]


def missing_impact(missing: list[str], claims: list[Claim], edges: list[Relationship]) -> dict[str, str]:
    """For each missing variable, what it would resolve - computed from the knowledge base."""
    dim_for_var = {"annual_rainfall_mm": "rainfall", "texture_class": "soil_texture",
                   "land_use_class": "system", "climate_zone": "climate_zone"}
    out = {}
    for v in missing:
        parts = []
        dim = dim_for_var.get(v)
        if dim:
            n = sum(1 for c in claims if dim in c.critical_dimensions)
            if n:
                parts.append(f"it is a load-bearing context dimension for {n} claims, which cannot be "
                             f"accepted or rejected without it")
        n_edges = sum(1 for e in edges if e.from_variable == v or e.to_variable == v)
        if n_edges:
            parts.append(f"it appears in {n_edges} causal pathways used to rank drivers")
        n_target = sum(1 for c in claims if c.target_metric == v)
        if n_target:
            parts.append(f"{n_target} interventions target it directly")
        if v == "annual_rainfall_mm":
            parts.append("it determines the climate zone when no coordinates are given")
        out[v] = "; ".join(parts) or "required input for suitability scoring"
    return out
