"""Claim vs site context matching (CLAUDE.md 4.4). Pure functions.

A mismatch on a critical dimension DISQUALIFIES the claim. Non-critical
dimensions only contribute to a soft 0-1 score. Unknown site values never
disqualify; they are flagged and scored as half-matches.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Claim, ClaimMatch, SiteState

DIMENSIONS = ["climate_zone", "rainfall", "soil_texture", "system"]
RAINFALL_SOFT_SCALE_MM = 400.0   # distance outside range at which soft rainfall score reaches 0
UNKNOWN_SCORE = 0.5


def site_system(site: SiteState) -> str | None:
    """Production-system label used in claim ctx_system (scope is rainfed cropland)."""
    if site.land_use_class == "agroforestry":
        return "agroforestry"
    if site.land_use_class == "grassland":
        return "rangeland"
    if site.land_use_class is None:
        return None
    return "rainfed"


@dataclass
class DimResult:
    applies: bool          # claim specifies this dimension at all
    known: bool            # site value is known
    score: float           # 0-1
    flag: str | None = None


def _dim(claim: Claim, site: SiteState, dim: str) -> DimResult:
    if dim == "climate_zone":
        allowed, value = claim.ctx_climate_zone, site.climate_zone
    elif dim == "soil_texture":
        allowed, value = claim.ctx_soil_texture, site.texture_class
    elif dim == "system":
        allowed, value = claim.ctx_system, site_system(site)
    elif dim == "rainfall":
        lo, hi = claim.ctx_rainfall_min, claim.ctx_rainfall_max
        if lo is None and hi is None:
            return DimResult(False, True, 1.0)
        r = site.annual_rainfall_mm
        if r is None:
            return DimResult(True, False, UNKNOWN_SCORE, "rainfall_unknown")
        lo = lo if lo is not None else float("-inf")
        hi = hi if hi is not None else float("inf")
        if lo <= r <= hi:
            return DimResult(True, True, 1.0)
        dist = lo - r if r < lo else r - hi
        return DimResult(True, True, round(max(0.0, 1 - dist / RAINFALL_SOFT_SCALE_MM), 2), "rainfall_mismatch")
    else:
        raise ValueError(dim)

    if not allowed:
        return DimResult(False, True, 1.0)
    if value is None:
        return DimResult(True, False, UNKNOWN_SCORE, f"{dim}_unknown")
    if value in allowed:
        return DimResult(True, True, 1.0)
    return DimResult(True, True, 0.0, f"{dim}_mismatch")


@dataclass
class MatchResult:
    disqualified: bool
    reason: str | None
    score: float
    flags: list[str] = field(default_factory=list)


def context_match(claim: Claim, site: SiteState) -> MatchResult:
    results = {d: _dim(claim, site, d) for d in DIMENSIONS}
    flags = [r.flag for r in results.values() if r.flag]

    for dim in claim.critical_dimensions:
        r = results[dim]
        if r.applies and r.known and r.flag and r.flag.endswith("_mismatch"):
            return MatchResult(True, _reason(claim, site, dim), 0.0, flags)

    soft = [r.score for d, r in results.items() if r.applies and d not in claim.critical_dimensions]
    # critical dims that are unknown lower confidence in applicability as well
    soft += [UNKNOWN_SCORE for d in claim.critical_dimensions if results[d].applies and not results[d].known]
    score = round(sum(soft) / len(soft), 2) if soft else 1.0
    return MatchResult(False, None, score, flags)


def _reason(claim: Claim, site: SiteState, dim: str) -> str:
    if dim == "rainfall":
        return (f"rainfall_mismatch: evidence measured at {claim.ctx_rainfall_min}-{claim.ctx_rainfall_max} mm, "
                f"site receives {site.annual_rainfall_mm} mm, and rainfall is load-bearing for this mechanism")
    site_val = {"climate_zone": site.climate_zone, "soil_texture": site.texture_class,
                "system": site_system(site)}[dim]
    allowed = {"climate_zone": claim.ctx_climate_zone, "soil_texture": claim.ctx_soil_texture,
               "system": claim.ctx_system}[dim]
    return (f"{dim}_mismatch: evidence applies to {'/'.join(allowed)}, site is {site_val}, "
            f"and {dim} is load-bearing for this mechanism")


def to_claim_match(claim: Claim, result: MatchResult, source_title: str) -> ClaimMatch:
    return ClaimMatch(
        claim_id=claim.id, intervention=claim.intervention, target_metric=claim.target_metric,
        direction=claim.direction, effect_min=claim.effect_min, effect_max=claim.effect_max,
        effect_unit=claim.effect_unit, time_horizon=claim.time_horizon,
        context_match_score=result.score, context_flags=result.flags,
        disqualified=result.disqualified, disqualify_reason=result.reason,
        evidence_strength=claim.evidence_strength, source_id=claim.source_id,
        source_title=source_title, page=claim.page, mechanism=claim.mechanism,
        verified=claim.verified,
    )
