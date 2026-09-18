"""Intervention selection, sequencing and transfer warnings (CLAUDE.md 4.6-4.7). Pure functions."""
from __future__ import annotations

from app.models import ClaimMatch, EvidenceEffect, Intervention, MetricTarget, SequenceStep, SiteState, Threshold
from app.reasoning.diagnosis import DiagnosisResult
from app.reasoning.suitability import target_for

WATER_VARIABLES = {"moisture_percent", "annual_rainfall_mm", "rainfall_pattern", "drought_frequency"}
WATER_LIMITED_CUTOFF = 0.4
STRENGTH_WEIGHT = {"meta_analysis": 1.0, "multi_site": 0.8, "single_site": 0.6, "modelled": 0.4}
HORIZON_ORDER = {"short": 0, "medium": 1, "long": 2}
MAX_PER_STAGE = 4
METRIC_UNITS = {"soc_percent": "%", "moisture_percent": "% volumetric", "annual_rainfall_mm": "mm",
                "mean_temp_c": "degC", "species_richness_index": "species per survey",
                "habitat_diversity_index": "index 0-1", "ndvi_proxy": "index 0-1", "ph": "pH"}
PRESSURE_ABSENT_CUTOFF = 0.7
TOP_DRIVERS_FOR_RELEVANCE = 3
ADVERSE_PENALTY = 0.3
EXTRA_METRIC_BONUS = 0.1


def relevant_metrics(diag: DiagnosisResult) -> set[str]:
    """Metrics on the causal paths of the top supporting drivers, plus the outcome."""
    metrics = {diag.outcome_variable}
    supporting = [d for d in diag.drivers if d.supports_concern][:TOP_DRIVERS_FOR_RELEVANCE]
    for d in supporting:
        metrics.update(d.path)
    if diag.limiting_factor:
        metrics.add(diag.limiting_factor)
    return metrics


def water_limited(diag: DiagnosisResult) -> bool:
    if diag.limiting_factor in WATER_VARIABLES:
        return True
    return any(diag.suitability.get(v, 1.0) < WATER_LIMITED_CUTOFF for v in WATER_VARIABLES)


def relief_metrics(diag: DiagnosisResult) -> set[str]:
    """The limiting factor itself, plus the next node on its pathway (rainfall cannot be
    changed by management, but the soil moisture it feeds can)."""
    lf = diag.limiting_factor
    if lf is None:
        return set()
    out = {lf}
    d = next((d for d in diag.drivers if d.variable == lf), None)
    if d and len(d.path) > 1:
        out.add(d.path[1])
    if lf in WATER_VARIABLES:
        out.add("moisture_percent")
    return out


def claim_weight(c: ClaimMatch) -> float:
    return STRENGTH_WEIGHT.get(c.evidence_strength, 0.4) * c.context_match_score


def metric_targets(metrics: list[str], site: SiteState, thresholds: list[Threshold]) -> list[MetricTarget]:
    """Measurable goal per improved metric, read from the thresholds table with its source."""
    out = []
    for m in metrics:
        t = target_for(m, site, thresholds)
        if t is None:
            continue
        target, source_id, note = t
        out.append(MetricTarget(variable=m, current=getattr(site, m, None), target=target,
                                unit=METRIC_UNITS.get(m), source_id=source_id, note=note))
    return out


def evidence_effects(claims: list[ClaimMatch]) -> list[EvidenceEffect]:
    return [EvidenceEffect(claim_id=c.claim_id, target_metric=c.target_metric, effect_min=c.effect_min,
                           effect_max=c.effect_max, effect_unit=c.effect_unit, time_horizon=c.time_horizon,
                           verified=c.verified, context_match_score=c.context_match_score)
            for c in claims if c.effect_min is not None and c.effect_max is not None]


def sequence(diag: DiagnosisResult, eligible: list[ClaimMatch], interventions: dict[str, Intervention],
             site: SiteState | None = None, thresholds: list[Threshold] | None = None
             ) -> tuple[list[SequenceStep], list[ClaimMatch]]:
    """Returns ordered steps and the eligible claims actually used to support them."""
    metrics = relevant_metrics(diag)
    relief = relief_metrics(diag)
    wl = water_limited(diag)
    lf = diag.limiting_factor
    lf_score = diag.suitability.get(lf) if lf else None

    by_intervention: dict[str, list[ClaimMatch]] = {}
    for c in eligible:
        if c.target_metric in metrics:
            by_intervention.setdefault(c.intervention, []).append(c)

    candidates = []
    for name, claims in by_intervention.items():
        improving = [c for c in claims if c.direction == "increase"]
        adverse = [c for c in claims if c.direction == "decrease"]
        if not improving:
            continue
        best = max(claim_weight(c) for c in improving)
        n_metrics = len({c.target_metric for c in improving})
        score = best + EXTRA_METRIC_BONUS * (n_metrics - 1) - ADVERSE_PENALTY * max(
            (claim_weight(c) for c in adverse), default=0.0)
        meta = interventions.get(name)
        if meta and meta.addresses_variable and diag.suitability.get(meta.addresses_variable, 1.0) >= PRESSURE_ABSENT_CUTOFF:
            continue  # the pressure it removes is absent or unobserved: recommending it would be speculative
        targets = sorted({c.target_metric for c in improving})
        if wl and meta and meta.competes_for_water:
            stage = 3
        elif relief & set(targets):
            stage = 1
        else:
            stage = 2
        direct = 0 if (lf in targets or (meta and meta.addresses_variable == lf)) else 1
        candidates.append((stage, direct, -round(score, 3), name, improving, adverse, targets, meta))

    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    # Cap stages 1-2 so the list stays actionable; always show deferred items so the
    # reason for deferral is visible rather than silently dropped.
    kept = [c for c in candidates if c[0] == 1][:MAX_PER_STAGE] + \
           [c for c in candidates if c[0] == 2][:MAX_PER_STAGE] + \
           [c for c in candidates if c[0] == 3]
    steps: list[SequenceStep] = []
    used: list[ClaimMatch] = []
    for i, (stage, _direct, _neg, name, improving, adverse, targets, meta) in enumerate(kept, start=1):
        if stage == 1:
            stage_name = "relieve_limiting_constraint"
            why = (f"Addresses the limiting constraint ({lf}, suitability {lf_score}) by improving "
                   f"{', '.join(t for t in targets if t in relief) or ', '.join(targets)}.")
        elif stage == 2:
            stage_name = "act_on_ranked_drivers"
            why = (f"Improves {', '.join(targets)}, which lie on the causal pathway to "
                   f"{diag.outcome_variable}; sequenced after the limiting constraint is addressed.")
        else:
            stage_name = "defer_until_water_constraint_relieved"
            why = (f"Deferred despite supporting evidence: {meta.note} ({meta.source_id}). "
                   f"Soil water is the scarce resource at this site, so establishing new biomass "
                   f"before moisture-conservation measures take effect competes for it.")
        if adverse:
            why += " Caveat: context-valid evidence also shows it can decrease " + ", ".join(
                f"{c.target_metric} ({c.claim_id})" for c in adverse) + "."
        horizon = min((c.time_horizon for c in improving), key=lambda h: HORIZON_ORDER[h])
        steps.append(SequenceStep(
            order=i, intervention=name, stage=stage_name, rationale=why, target_metrics=targets,
            time_horizon=horizon, claim_ids=[c.claim_id for c in improving + adverse],
            metric_targets=metric_targets(targets, site, thresholds) if site and thresholds else [],
            evidence_effects=evidence_effects(improving),
        ))
        used.extend(improving + adverse)
    return steps, used


def transfer_warnings(eligible: list[ClaimMatch], used: list[ClaimMatch], rejected: list[ClaimMatch],
                      diag: DiagnosisResult) -> list[str]:
    """Every eligible claim carrying a number from a non-matching context gets a warning,
    because eligible claims are shown in the output even when not sequenced."""
    warnings = []
    for c in eligible:
        if c.effect_min is None and c.effect_max is None:
            continue
        if c.context_match_score < 1.0 or c.context_flags:
            flags = ", ".join(c.context_flags) or "partial context match"
            warnings.append(
                f"{c.claim_id} ({c.intervention} -> {c.target_metric}): the direction of the effect is "
                f"supported, but the magnitude ({c.effect_min}-{c.effect_max} {c.effect_unit}) comes from a "
                f"context that differs from this site ({flags}; match {c.context_match_score}) and should "
                f"not be assumed to transfer.")
    metrics = relevant_metrics(diag)
    used_metrics = {c.target_metric for c in used if c.direction == "increase"}
    for m in sorted(metrics):
        n_rej = sum(1 for c in rejected if c.target_metric == m)
        if m not in used_metrics and n_rej:
            warnings.append(
                f"No context-valid evidence was found for improving {m}: {n_rej} claim(s) were rejected "
                f"on load-bearing context dimensions (see rejected evidence).")
    return warnings
