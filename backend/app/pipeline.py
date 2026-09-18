"""Assessment assembly: SiteState -> Assessment. Deterministic; no LLM anywhere in this file.

Retrieval (store calls) happens here; all judgement happens in app/reasoning/.
"""
from __future__ import annotations

from app.models import Assessment, ConfidenceBreakdown, Measurement, SiteState
from app.reasoning.confidence import confidence, missing_critical, missing_impact
from app.reasoning.context_match import context_match, to_claim_match
from app.reasoning.diagnosis import DEFAULT_CONCERN, rank_drivers
from app.reasoning.selector import relevant_metrics, sequence, transfer_warnings
from app.reasoning.suitability import UPPER_SUFFIX
from app.reasoning.zone import zone_from_rainfall


def resolve_zone(site: SiteState, store) -> SiteState:
    site = site.model_copy(deep=True)
    if site.climate_zone is None and site.lat is not None and site.lon is not None:
        z = store.zone_for(site.lat, site.lon)
        if z:
            site.climate_zone = z
            site.field_sources["climate_zone"] = "geo_lookup"
    if site.climate_zone is None and site.annual_rainfall_mm is not None:
        site.climate_zone = zone_from_rainfall(site.annual_rainfall_mm)
        site.field_sources["climate_zone"] = "derived"
    return site


def assess(site: SiteState, store, measurements: list[Measurement] | None = None) -> tuple[Assessment, SiteState]:
    site = resolve_zone(site, store)
    thresholds = store.thresholds()
    edges = store.relationships()
    scoring_vars = sorted({t.variable for t in thresholds if not t.variable.endswith(UPPER_SUFFIX)})

    missing = missing_critical(site)
    if missing:
        all_claims = store.all_claims()
        return Assessment(
            site_id=site.site_id, status="insufficient_data", limiting_factor=None,
            drivers_ranked=[], discriminating_measurement=None, eligible_claims=[],
            rejected_claims=[], recommended_sequence=[],
            confidence=ConfidenceBreakdown(
                level="low", n_supporting_claims=0, context_quality_mean=0.0,
                data_completeness=round(sum(site.known(v) for v in scoring_vars) / len(scoring_vars), 2),
                n_conflicts=0, rationale=["critical variables missing; no recommendation produced"]),
            transfer_warnings=[], missing_variables=missing,
            missing_variable_impact=missing_impact(missing, all_claims, edges),
        ), site

    if measurements is None:
        measurements = store.measurements(site.site_id)
    concern = site.concern or DEFAULT_CONCERN
    diag = rank_drivers(site, edges, thresholds, measurements, concern)

    metrics = sorted(relevant_metrics(diag))
    claims = store.claims_for_metrics(metrics)
    titles = store.source_titles()
    matches = [to_claim_match(c, context_match(c, site), titles.get(c.source_id, c.source_id)) for c in claims]
    eligible = [m for m in matches if not m.disqualified]
    rejected = [m for m in matches if m.disqualified]

    steps, used = sequence(diag, eligible, store.interventions(), site, thresholds)
    optional_missing = [v for v in scoring_vars if not site.known(v)]
    passages = {s.intervention: store.semantic_passages(
        f"{s.intervention.replace('_', ' ')} improves {' and '.join(m.replace('_', ' ') for m in s.target_metrics)}")
        for s in steps}

    assessment = Assessment(
        site_id=site.site_id,
        status="complete",
        suitability=diag.suitability,
        limiting_factor=diag.limiting_factor,
        drivers_ranked=diag.drivers,
        under_determined=diag.under_determined,
        discriminating_measurement=diag.discriminating_measurement,
        hypothesis_note=diag.hypothesis_note,
        eligible_claims=eligible,
        rejected_claims=rejected,
        recommended_sequence=[s.intervention for s in steps],
        sequence_detail=steps,
        confidence=confidence(used, eligible, site, scoring_vars, diag.under_determined),
        transfer_warnings=transfer_warnings(eligible, used, rejected, diag),
        missing_variables=optional_missing,
        missing_variable_impact=missing_impact(optional_missing, claims, edges),
        supporting_passages=passages,
    )
    return assessment, site
