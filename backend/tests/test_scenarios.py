"""The four demo scenarios (CLAUDE.md 7.1) run end to end through the deterministic pipeline."""
import pytest

from app.pipeline import assess
from app.retrieval.store import CsvStore


@pytest.fixture(scope="module")
def store():
    return CsvStore()


def run(store, site_id, **overrides):
    site = store.get_site(site_id).model_copy(update=overrides)
    return assess(site, store)


def test_multistressor_sequences_water_before_diversification(store):
    a, site = run(store, "beed_wheat")
    assert site.climate_zone == "semi_arid" and site.field_sources["climate_zone"] == "geo_lookup"
    assert a.limiting_factor == "moisture_percent"
    # the top-ranked biodiversity driver is not the limiting factor - both are reported
    assert a.drivers_ranked[0].variable == "habitat_diversity_index"
    assert a.sequence_detail[0].stage == "relieve_limiting_constraint"
    assert "moisture_percent" in a.sequence_detail[0].target_metrics
    agro = next(s for s in a.sequence_detail if s.intervention == "agroforestry")
    assert agro.stage == "defer_until_water_constraint_relieved"
    assert agro.order == len(a.sequence_detail)
    # low grazing pressure -> grazing management not recommended
    assert "grazing_management" not in a.recommended_sequence
    # Vertisol-only claim rejected on a loamy site, kept visible
    assert any(c.claim_id == "C10" and c.disqualified for c in a.rejected_claims)


def test_user_hypothesis_ranked_not_rejected(store):
    a, _ = run(store, "anantapur_groundnut")
    assert a.drivers_ranked[0].variable == "habitat_diversity_index"
    assert "more strongly supports habitat_diversity_index" in a.hypothesis_note
    assert "does not rule pesticide_intensity out" in a.hypothesis_note
    assert a.discriminating_measurement
    assert a.recommended_sequence[0] == "field_margin_restoration"


def test_transfer_warning_keeps_direction_not_magnitude(store):
    a, _ = run(store, "dharwad_cotton")
    c14 = next(c for c in a.eligible_claims if c.claim_id == "C14")
    assert not c14.disqualified and c14.context_match_score < 1
    assert any(w.startswith("C14") and "should not be assumed to transfer" in w for w in a.transfer_warnings)


def test_same_cover_crop_claim_disqualified_in_drier_site(store):
    a, _ = run(store, "dharwad_cotton", annual_rainfall_mm=450)
    c14 = next(c for c in a.rejected_claims if c.claim_id == "C14")
    assert c14.disqualify_reason.startswith("rainfall_mismatch")


def test_insufficient_data_declines_to_recommend(store):
    a, _ = run(store, "unknown_plot")
    assert a.status == "insufficient_data"
    assert a.recommended_sequence == [] and a.eligible_claims == []
    assert set(a.missing_variables) == {"soc_percent", "annual_rainfall_mm", "texture_class", "habitat_diversity_index"}
    assert "load-bearing context dimension" in a.missing_variable_impact["annual_rainfall_mm"]


def test_assessment_is_deterministic(store):
    a1, _ = run(store, "beed_wheat")
    a2, _ = run(store, "beed_wheat")
    assert a1.model_dump() == a2.model_dump()
