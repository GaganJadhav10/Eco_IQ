"""Slot planner: templated clarifying questions for missing critical variables (CLAUDE.md 5.2).

Templated rather than LLM-generated so the conversation cannot drift off-script.
Questions are ordered by how much each variable unlocks in the knowledge base.
"""
from __future__ import annotations

QUESTIONS = {
    "soc_percent": "What is the soil organic carbon (SOC) from your latest soil test, as a percentage? "
                   "Soil Health Card reports list it as 'OC %'.",
    "annual_rainfall_mm": "Roughly how much rain does the site get in a normal year, in mm? "
                          "Alternatively, share the site's coordinates (lat, lon).",
    "texture_class": "What is the soil like: sandy, loamy, clayey, or black cotton soil (Vertisol)?",
    "land_use_class": "How is the land used: a single crop (monoculture), mixed cropping or intercropping, "
                      "agroforestry, grassland, or fallow?",
    "habitat_diversity_index": "How much non-crop habitat is around the fields, such as hedges, tree lines, "
                               "grassy strips or scrub patches? A rough 0-1 score works "
                               "(e.g. 0.1 = almost none, 0.5 = a lot).",
    # Non-critical, but each one unlocks more of the knowledge base.
    "moisture_percent": "What is the soil moisture, as a volumetric percentage, at the time of sampling?",
    "rainfall_pattern": "Has the rain been normal, low, or erratic in recent seasons?",
    "drought_frequency": "How often does the site face drought: rarely, sometimes, or frequently?",
    "pesticide_intensity": "How heavy is pesticide use on this land: low, moderate or high?",
    "fertilizer_intensity": "How heavy is fertiliser use: low, moderate or high?",
    "grazing_pressure": "How much livestock grazing does the land carry: none, low, moderate or high?",
    "fragmentation_level": "Is the surrounding landscape continuous or broken into isolated patches "
                           "(low, moderate or high fragmentation)?",
    "field_margin_present": "Are there uncropped field margins, hedges or bund vegetation around the plots?",
    "pollinator_observed": "How much pollinator activity do you see: none, low, moderate or high?",
    "species_richness_index": "Roughly how many species do you count in a standard walk-through survey?",
    "ndvi_proxy": "Do you have a greenness or NDVI value for the growing season (0-1)?",
    "cropping_intensity": "How many crops per year: a single crop, two crops, or continuous cropping?",
    "ph": "What is the soil pH from your latest soil test?",
    "mean_temp_c": "What is the mean annual temperature at the site, in degrees Celsius?",
}
MAX_QUESTIONS_PER_TURN = 2


def _impact_weight(text: str) -> int:
    import re
    return sum(int(n) for n in re.findall(r"\b(\d+)\b", text or ""))


def next_questions(missing: list[str], impact: dict[str, str]) -> list[str]:
    ordered = sorted(missing, key=lambda v: (-_impact_weight(impact.get(v, "")), v))
    return [QUESTIONS[v] for v in ordered if v in QUESTIONS][:MAX_QUESTIONS_PER_TURN]
