"""Output-quality requirements from the challenge brief: measurable targets, quantified effects,
clarifying questions, and follow-up questions about a named intervention."""
import pytest
from fastapi.testclient import TestClient

from app.extractor import asked_about, drop_question_artifacts, is_question, rule_extract
from app.main import app, intervention_focus
from app.narrator import template_narration
from app.pipeline import assess
from app.retrieval.store import CsvStore


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def beed():
    s = CsvStore()
    return assess(s.get_site("beed_wheat"), s)[0]


# ---------------------------------------------------------------- measurable targets
def test_every_step_carries_a_sourced_measurable_target(beed):
    for step in beed.sequence_detail:
        assert step.metric_targets, f"{step.intervention} has no target"
        for t in step.metric_targets:
            assert t.source_id and t.note
            assert t.target is not None


def test_target_uses_the_threshold_for_this_site(beed):
    target = next(t for s in beed.sequence_detail for t in s.metric_targets if t.variable == "moisture_percent")
    assert target.current == 13 and target.target == 25      # loam field capacity, FAO-56
    assert target.source_id == "fao56_1998"


def test_narration_states_targets_and_effects_or_says_there_are_none(beed):
    text = template_narration(beed)
    assert "Target for `moisture_percent`: 13 % volumetric -> 25 % volumetric (fao56_1998)" in text
    assert "Reported effect" in text or "No quantified effect size" in text


def test_quantified_effects_are_flagged_when_unverified(beed):
    effects = [e for s in beed.sequence_detail for e in s.evidence_effects]
    assert effects, "expected at least one quantified effect in the plan"
    assert all(e.effect_min <= e.effect_max for e in effects)
    assert "not yet source-verified" in template_narration(beed)


# ---------------------------------------------------------------- clarifying questions
def test_complete_assessment_still_asks_for_sharper_data(client):
    r = client.post("/api/assess", json={"site": {
        "soc_percent": 0.3, "annual_rainfall_mm": 520, "texture_class": "loamy",
        "land_use_class": "monoculture", "habitat_diversity_index": 0.15}}).json()
    assert r["assessment"]["status"] == "complete"
    assert 1 <= len(r["improvement_questions"]) <= 2
    assert r["improvement_impact"]


def test_insufficient_data_asks_for_the_critical_fields(client):
    r = client.post("/api/chat", json={"message": "We grow cotton with heavy pesticide use."}).json()
    assert r["assessment"]["status"] == "insufficient_data"
    assert r["questions"] and not r["improvement_questions"]


# ---------------------------------------------------------------- follow-up questions
def test_question_about_an_intervention_is_not_read_as_a_fact():
    assert is_question("What about agroforestry?")
    fields = rule_extract("What about agroforestry?")
    assert fields.get("land_use_class") == "agroforestry"          # the raw reader sees the word
    assert "land_use_class" not in drop_question_artifacts(fields, "What about agroforestry?")
    # a statement still sets it
    assert drop_question_artifacts(rule_extract("We practise agroforestry here."),
                                   "We practise agroforestry here.")["land_use_class"] == "agroforestry"


def test_asked_about_matches_intervention_names():
    assert set(asked_about("should we try cover crops or mulching?")) == {"cover_cropping", "mulching"}
    assert asked_about("nothing relevant here") == []


def test_focus_explains_a_deferred_and_an_adverse_intervention(beed):
    focus = {f["intervention"]: f for f in intervention_focus(beed.model_dump(),
                                                              ["agroforestry", "cover_cropping"])}
    assert focus["agroforestry"]["in_sequence"]
    assert "defer" in focus["agroforestry"]["verdict"]
    assert "wrong way" in focus["cover_cropping"]["verdict"]


def test_chat_follow_up_keeps_the_site_and_answers_the_question(client):
    r = client.post("/api/chat", json={"message": "what about agroforestry?", "site_id": "beed_wheat"}).json()
    assert r["site_state"]["land_use_class"] == "monoculture"
    assert r["focus"][0]["intervention"] == "agroforestry"
    assert r["reply"].startswith("**About agroforestry:**")
