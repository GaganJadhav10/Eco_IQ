"""Unit tests for the pure reasoning functions (no DB, no network, no LLM)."""
from app.models import Claim, ClaimMatch, Driver, Intervention, Measurement, Relationship, SiteState, Threshold
from app.reasoning.confidence import conflicts, missing_critical
from app.reasoning.context_match import context_match
from app.reasoning.diagnosis import DiagnosisResult, best_path, discriminating_measurement
from app.reasoning.selector import sequence, transfer_warnings, water_limited
from app.reasoning.suitability import geometric_index, limiting_factor, suitability
from app.reasoning.temporal import trend, trend_factor
from app.reasoning.zone import zone_from_rainfall

T = [
    Threshold(variable="soc_percent", poor=0.2, good=0.75, source_id="s", note=""),
    Threshold(variable="ph", poor=5.0, good=6.5, source_id="s", note=""),
    Threshold(variable="ph:upper", poor=9.0, good=7.5, source_id="s", note=""),
    Threshold(variable="moisture_percent", texture_class="sandy", poor=5, good=12, source_id="s", note=""),
    Threshold(variable="moisture_percent", poor=12, good=25, source_id="s", note=""),
    Threshold(variable="land_use_class", enum_scores={"monoculture": 0.2, "agroforestry": 1.0}, source_id="s", note=""),
    Threshold(variable="field_margin_present", enum_scores={"true": 1.0, "false": 0.3}, source_id="s", note=""),
]


def claim(**kw):
    base = dict(id="X", intervention="i", target_metric="soc_percent", direction="increase",
                time_horizon="medium", mechanism="m", evidence_strength="meta_analysis", source_id="s")
    base.update(kw)
    return Claim(**base)


def match(**kw):
    base = dict(claim_id="X", intervention="i", target_metric="moisture_percent", direction="increase",
                effect_min=None, effect_max=None, effect_unit=None, time_horizon="short",
                context_match_score=1.0, context_flags=[], disqualified=False, disqualify_reason=None,
                evidence_strength="meta_analysis", source_id="s", source_title="t", page=None)
    base.update(kw)
    return ClaimMatch(**base)


# ---------------------------------------------------------------- suitability
def test_linear_suitability_clamped():
    site = SiteState()
    assert suitability("soc_percent", 0.1, site, T) == 0.0
    assert suitability("soc_percent", 0.475, site, T) == 0.5
    assert suitability("soc_percent", 2.0, site, T) == 1.0


def test_ph_optimum_band_uses_both_sides():
    site = SiteState()
    assert suitability("ph", 7.0, site, T) == 1.0
    assert suitability("ph", 8.25, site, T) == 0.5
    assert suitability("ph", 5.75, site, T) == 0.5


def test_texture_specific_threshold_wins_over_wildcard():
    assert suitability("moisture_percent", 12, SiteState(texture_class="sandy"), T) == 1.0
    assert suitability("moisture_percent", 12, SiteState(texture_class="loamy"), T) == 0.0


def test_enum_and_bool_scores():
    assert suitability("land_use_class", "monoculture", SiteState(), T) == 0.2
    assert suitability("field_margin_present", False, SiteState(), T) == 0.3


def test_unknown_value_returns_none():
    assert suitability("soc_percent", None, SiteState(), T) is None


def test_limiting_factor_is_minimum_with_deterministic_tie_break():
    assert limiting_factor({"b": 0.2, "a": 0.2, "c": 0.9}) == "a"
    assert limiting_factor({}) is None
    assert geometric_index({"a": 1.0, "b": 0.25}) == 0.5


# ---------------------------------------------------------------- temporal
def _m(values):
    return [Measurement(site_id="s", variable="v", value=v, date=f"202{i}-01-01") for i, v in enumerate(values)]


def test_trend_detection():
    assert trend(_m([10, 8, 6])) == "declining"
    assert trend(_m([10, 10.1, 10])) == "stable"
    assert trend(_m([5, 7, 9])) == "improving"
    assert trend(_m([5])) is None


def test_trend_factor_rewards_co_decline_only_when_outcome_declines():
    assert trend_factor("declining", "declining") > 1
    assert trend_factor("improving", "declining") < 1
    assert trend_factor("declining", None) == 1.0


# ---------------------------------------------------------------- causal paths
EDGES = [
    Relationship(id="1", from_variable="a", to_variable="b", weight=0.5, mechanism="", source_id="s"),
    Relationship(id="2", from_variable="b", to_variable="goal", weight=0.8, mechanism="", source_id="s"),
    Relationship(id="3", from_variable="a", to_variable="goal", weight=0.3, mechanism="", source_id="s"),
    Relationship(id="4", from_variable="c", to_variable="goal", weight=0.9, ctx_soil_texture=["sandy"],
                 mechanism="", source_id="s"),
]


def test_best_path_picks_highest_weight_product():
    support, path = best_path("a", "goal", EDGES, SiteState())
    assert support == 0.4 and [e.id for e in path] == ["1", "2"]


def test_edge_blocked_by_known_context_mismatch_but_not_unknown():
    assert best_path("c", "goal", EDGES, SiteState(texture_class="clayey"))[0] == 0
    assert best_path("c", "goal", EDGES, SiteState())[0] == 0.9


def test_discriminating_measurement_prefers_unmeasured_intermediate():
    a = Driver(variable="a", suitability_score=0.2, supports_concern=True, temporal_trend=None, assumption="",
               path=["a", "b", "goal"])
    c = Driver(variable="c", suitability_score=0.2, supports_concern=True, temporal_trend=None, assumption="",
               path=["c", "goal"])
    msg = discriminating_measurement(a, c, SiteState(), "goal", {})
    assert msg.startswith("Measure b")


# ---------------------------------------------------------------- context matching
def test_critical_dimension_mismatch_disqualifies():
    c = claim(ctx_rainfall_min=600, ctx_rainfall_max=1500, critical_dimensions=["rainfall"])
    r = context_match(c, SiteState(annual_rainfall_mm=450))
    assert r.disqualified and r.reason.startswith("rainfall_mismatch")


def test_non_critical_mismatch_only_lowers_score():
    c = claim(ctx_rainfall_min=600, ctx_rainfall_max=1500, ctx_climate_zone=["humid"])
    r = context_match(c, SiteState(annual_rainfall_mm=450, climate_zone="semi_arid"))
    assert not r.disqualified and 0 < r.score < 1
    assert "climate_zone_mismatch" in r.flags


def test_unknown_critical_context_does_not_disqualify():
    c = claim(ctx_soil_texture=["vertisol"], critical_dimensions=["soil_texture"])
    r = context_match(c, SiteState())
    assert not r.disqualified and r.score == 0.5


# ---------------------------------------------------------------- selection
def _diag(lf="moisture_percent", suit=None):
    return DiagnosisResult(
        outcome_variable="species_richness_index", suitability=suit or {"moisture_percent": 0.1, "land_use_class": 0.2},
        limiting_factor=lf,
        drivers=[Driver(variable="land_use_class", suitability_score=0.2, supports_concern=True, temporal_trend=None,
                        assumption="", path=["land_use_class", "species_richness_index"]),
                 Driver(variable="moisture_percent", suitability_score=0.1, supports_concern=True,
                        temporal_trend=None, assumption="",
                        path=["moisture_percent", "ndvi_proxy", "species_richness_index"])],
        under_determined=False, discriminating_measurement=None, hypothesis_note=None)


INTERVENTIONS = {
    "mulch": Intervention(id="mulch", label="", category="water_conservation", competes_for_water=False,
                          note="", source_id="s"),
    "trees": Intervention(id="trees", label="", category="diversification", competes_for_water=True,
                          addresses_variable="land_use_class", note="roots compete", source_id="s"),
    "graze": Intervention(id="graze", label="", category="grazing", competes_for_water=False,
                          addresses_variable="grazing_pressure", note="", source_id="s"),
}


def test_water_limited_site_defers_water_competing_intervention():
    eligible = [match(claim_id="A", intervention="trees", target_metric="species_richness_index",
                      evidence_strength="meta_analysis"),
                match(claim_id="B", intervention="mulch", target_metric="moisture_percent",
                      evidence_strength="single_site")]
    steps, _ = sequence(_diag(), eligible, INTERVENTIONS)
    assert [s.intervention for s in steps] == ["mulch", "trees"]
    assert steps[1].stage == "defer_until_water_constraint_relieved"


def test_not_water_limited_does_not_defer():
    d = _diag(lf="land_use_class", suit={"moisture_percent": 0.9, "land_use_class": 0.2})
    assert not water_limited(d)
    eligible = [match(claim_id="A", intervention="trees", target_metric="species_richness_index")]
    steps, _ = sequence(d, eligible, INTERVENTIONS)
    assert steps[0].stage == "relieve_limiting_constraint"


def test_intervention_skipped_when_its_pressure_is_absent():
    d = _diag(suit={"moisture_percent": 0.1, "land_use_class": 0.2, "grazing_pressure": 1.0})
    eligible = [match(claim_id="G", intervention="graze", target_metric="species_richness_index")]
    steps, _ = sequence(d, eligible, INTERVENTIONS)
    assert steps == []


def test_transfer_warning_only_for_quantified_mismatched_claims():
    exact = match(claim_id="E", effect_min=1, effect_max=2, effect_unit="u")
    soft = match(claim_id="S", effect_min=1, effect_max=2, effect_unit="u", context_match_score=0.5,
                 context_flags=["climate_zone_mismatch"])
    unquantified = match(claim_id="U", context_match_score=0.5, context_flags=["climate_zone_mismatch"])
    w = transfer_warnings([exact, soft, unquantified], [exact, soft], [], _diag())
    assert len([x for x in w if x.startswith(("E ", "S ", "U "))]) == 1 and w[0].startswith("S ")


def test_conflicts_counted_per_intervention_metric():
    cs = [match(intervention="cc", direction="increase"), match(intervention="cc", direction="decrease"),
          match(intervention="mulch")]
    assert conflicts(cs) == [("cc", "moisture_percent")]


def test_missing_critical_and_zone():
    assert "soc_percent" in missing_critical(SiteState())
    assert zone_from_rainfall(600) == "semi_arid" and zone_from_rainfall(1200) == "sub_humid"
    assert zone_from_rainfall(None) is None
