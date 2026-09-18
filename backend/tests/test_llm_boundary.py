"""The LLM boundary: extraction never guesses, narration never adds facts."""
import pytest

from app.extractor import rule_extract
from app.llm import LLMService
from app.narrator import narrate, numeric_guard, template_narration
from app.pipeline import assess
from app.retrieval.store import CsvStore


class FakeLLM(LLMService):
    def __init__(self, replies):
        super().__init__(api_key="fake")
        self.replies = list(replies)

    def generate_text(self, system, user, temperature=0.2):
        return self.replies.pop(0)


@pytest.fixture(scope="module")
def beed():
    s = CsvStore()
    return assess(s.get_site("beed_wheat"), s)[0]


def test_rule_extractor_reads_explicit_values():
    f = rule_extract("Our wheat monoculture near Beed gets about 520 mm of erratic rain, SOC is 0.32%, "
                     "soil is loamy, pH 8.1, heavy pesticide use and no hedges. Birds are declining.")
    assert f["annual_rainfall_mm"] == 520 and f["soc_percent"] == 0.32 and f["ph"] == 8.1
    assert f["texture_class"] == "loamy" and f["land_use_class"] == "monoculture" and f["crop_system"] == "wheat"
    assert f["rainfall_pattern"] == "erratic" and f["pesticide_intensity"] == "high"
    assert f["field_margin_present"] is False and f["concern"] == "biodiversity_decline"


def test_rule_extractor_does_not_guess_from_vague_language():
    f = rule_extract("The soil feels quite dry and the farm is not doing well.")
    assert "moisture_percent" not in f and "soc_percent" not in f and "annual_rainfall_mm" not in f


def test_hypothesis_needs_causal_language():
    assert rule_extract("I'm sure the pesticides are killing biodiversity")["user_hypothesis"] == "pesticide_intensity"
    assert "user_hypothesis" not in rule_extract("We use moderate pesticide.")


def test_guard_accepts_faithful_rephrasing(beed):
    t = template_narration(beed)
    ok = f"The scarcest factor is moisture_percent with suitability {beed.suitability['moisture_percent']}."
    assert numeric_guard(ok, beed, t)["passed"]


def test_guard_rejects_invented_number_and_identifier(beed):
    t = template_narration(beed)
    r = numeric_guard("Mulching raises soil moisture by 47% (see smith_2019).", beed, t)
    assert not r["passed"] and "47" in r["unsupported_numbers"] and "smith_2019" in r["unsupported_identifiers"]


def test_corrupted_narration_falls_back_to_template(beed):
    out = narrate(beed, FakeLLM(["SOC will rise by 2.53 t/ha.", "Yields improve 47.8% within 993 days."]))
    assert out["mode"] == "template_fallback"
    assert out["text"] == template_narration(beed)
    assert len(out["guard"]) == 2 and not any(g["passed"] for g in out["guard"])


def test_disabled_llm_gives_identical_science(beed):
    out = narrate(beed, LLMService(api_key=""))
    assert out["mode"] == "template"
