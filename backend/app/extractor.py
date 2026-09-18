"""Extractor: free text -> partial SiteState fields (CLAUDE.md 5.1).

Only fields the message explicitly states are returned. Nothing is inferred or
defaulted. Gemini JSON mode is used when available; a deterministic rule-based
extractor is the fallback, and is also what the tests exercise.
"""
from __future__ import annotations

import re
from typing import get_args

from pydantic import ValidationError

from app.llm import LLMError, LLMService
from app.models import SiteState

EXTRACTABLE = [
    "lat", "lon", "concern", "user_hypothesis",
    "soc_percent", "ph", "moisture_percent", "texture_class", "annual_rainfall_mm", "rainfall_pattern",
    "mean_temp_c", "drought_frequency", "land_use_class", "crop_system", "cropping_intensity",
    "field_margin_present", "species_richness_index", "habitat_diversity_index", "pollinator_observed",
    "ndvi_proxy", "fertilizer_intensity", "pesticide_intensity", "grazing_pressure", "fragmentation_level",
]
CONCERNS = ["biodiversity_decline", "pollinator_decline", "soil_degradation", "vegetation_decline"]
HYPOTHESIS_VARIABLES = ["pesticide_intensity", "fertilizer_intensity", "grazing_pressure", "fragmentation_level",
                        "land_use_class", "rainfall_pattern", "drought_frequency", "soc_percent",
                        "habitat_diversity_index", "field_margin_present", "mean_temp_c"]


# --------------------------------------------------------------------------- rule-based
NUM = r"(\d+(?:\.\d+)?)"
LEVEL_WORDS = {"heavy": "high", "high": "high", "intensive": "high", "intense": "high", "a lot of": "high",
               "lots of": "high", "excessive": "high", "moderate": "moderate", "some": "moderate",
               "medium": "moderate", "low": "low", "little": "low", "minimal": "low", "light": "low", "no": "none"}
CROPS = ["wheat", "cotton", "groundnut", "peanut", "sorghum", "jowar", "bajra", "pearl millet", "millet", "maize",
         "soybean", "chickpea", "pigeonpea", "rice", "paddy", "sugarcane", "sunflower", "ragi", "mustard"]


def _level(word: str, allow_none: bool) -> str | None:
    lvl = LEVEL_WORDS.get(word.lower())
    if lvl == "none" and not allow_none:
        return "low"
    return lvl


def rule_extract(text: str) -> dict:
    t = text.lower()
    out: dict = {}

    def num(pattern):
        m = re.search(pattern, t)
        return float(m.group(1)) if m else None

    out["soc_percent"] = num(r"(?:\bsoc\b|soil organic carbon|organic carbon)[^\d%]{0,25}?" + NUM + r"\s*%")
    out["ph"] = num(r"\bph\b[^\d]{0,12}?" + NUM)
    out["moisture_percent"] = num(r"moisture[^\d%]{0,25}?" + NUM + r"\s*%")
    out["annual_rainfall_mm"] = num(NUM + r"\s*mm")
    out["mean_temp_c"] = num(NUM + r"\s*(?:°\s*c\b|degrees? c(?:elsius)?\b|deg c\b|celsius)")
    out["species_richness_index"] = num(NUM + r"\s+(?:\w+\s+)?species\b")
    out["habitat_diversity_index"] = num(r"habitat (?:diversity )?(?:index )?[^\d]{0,12}?(0?\.\d+|0|1(?:\.0)?)\b")
    out["ndvi_proxy"] = num(r"ndvi[^\d]{0,12}?(0?\.\d+)")
    m = re.search(r"(-?\d{1,2}\.\d+)\s*°?\s*n?\s*[, ]\s*(-?\d{2,3}\.\d+)\s*°?\s*e?", t)
    if m:
        out["lat"], out["lon"] = float(m.group(1)), float(m.group(2))

    if re.search(r"vertisol|black cotton soil|black soil", t):
        out["texture_class"] = "vertisol"
    elif re.search(r"\bsand(y)?\b", t):
        out["texture_class"] = "sandy"
    elif re.search(r"\bclay(ey)?\b", t):
        out["texture_class"] = "clayey"
    elif re.search(r"\bloam(y)?\b", t):
        out["texture_class"] = "loamy"

    if re.search(r"erratic|irregular|unpredictable", t):
        out["rainfall_pattern"] = "erratic"
    elif re.search(r"(below.normal|deficient|scanty) (rain|monsoon)", t):
        out["rainfall_pattern"] = "low"
    elif re.search(r"normal (rain|monsoon)", t):
        out["rainfall_pattern"] = "normal"

    if re.search(r"(frequent|recurring|repeated|regular) droughts?", t):
        out["drought_frequency"] = "high"
    elif re.search(r"(occasional|some) droughts?", t):
        out["drought_frequency"] = "moderate"
    elif re.search(r"(rare|no) droughts?", t):
        out["drought_frequency"] = "low"

    if re.search(r"agroforestry", t):
        out["land_use_class"] = "agroforestry"
    elif re.search(r"mono.?(culture|crop)", t):
        out["land_use_class"] = "monoculture"
    elif re.search(r"mixed.cropping|intercrop", t):
        out["land_use_class"] = "mixed_cropping"
    elif re.search(r"grassland|pasture", t):
        out["land_use_class"] = "grassland"
    elif re.search(r"\bfallow\b", t):
        out["land_use_class"] = "fallow"

    for crop in CROPS:
        if re.search(rf"\b{crop}\b", t):
            out["crop_system"] = crop
            break

    if re.search(r"continuous(ly)? crop", t):
        out["cropping_intensity"] = "continuous"
    elif re.search(r"(two|double) crops?|double.cropp", t):
        out["cropping_intensity"] = "double"
    elif re.search(r"(one|single) crop|single.cropp", t):
        out["cropping_intensity"] = "single"

    if re.search(r"\b(no|without|removed|cleared)\b[^.]{0,20}(hedge|field margin|margin|boundary vegetation|bund vegetation)", t):
        out["field_margin_present"] = False
    elif re.search(r"hedgerow|field margins?|hedges", t):
        out["field_margin_present"] = True

    if re.search(r"\bno (bees|pollinators)\b", t):
        out["pollinator_observed"] = "none"
    elif re.search(r"\b(few|fewer|rarely see|declining) (bees|pollinators)\b", t):
        out["pollinator_observed"] = "low"
    elif re.search(r"\b(many|lots of|plenty of) (bees|pollinators)\b", t):
        out["pollinator_observed"] = "high"

    words = "|".join(sorted(map(re.escape, LEVEL_WORDS), key=len, reverse=True))
    for field, noun, allow_none in [("pesticide_intensity", r"(?:pesticides?|insecticides?|spraying)", False),
                                    ("fertilizer_intensity", r"(?:fertili[sz]ers?|urea|dap)", False),
                                    ("grazing_pressure", r"(?:grazing|livestock pressure)", True)]:
        m = re.search(rf"\b({words})\s+(?:use of\s+)?{noun}", t) or \
            re.search(rf"{noun}\s+(?:use\s+)?(?:is\s+|are\s+)?(?:very\s+)?({words})\b", t)
        if m:
            out[field] = _level(m.group(1), allow_none)
    if re.search(r"(highly |very )?fragmented|isolated patch", t):
        out["fragmentation_level"] = "high"

    if re.search(r"\bbees?\b|pollinat", t):
        out["concern"] = "pollinator_decline"
    elif re.search(r"(soil (carbon|organic|health|fertility)|\bsoc\b)[^.]{0,40}(fall|declin|drop|loss|losing|poor)"
                   r"|soil degrad", t):
        out["concern"] = "soil_degradation"
    elif re.search(r"biodiversity|species|\bbirds?\b|\binsects?\b|wildlife", t):
        out["concern"] = "biodiversity_decline"
    elif re.search(r"greenness|ndvi|vegetation|yield", t):
        out["concern"] = "vegetation_decline"

    if re.search(r"because of|due to|caused by|blame|i think|i'm sure|i am sure|killing|responsible|the reason", t):
        for kw, var in [("pesticid", "pesticide_intensity"), ("insecticid", "pesticide_intensity"),
                        ("fertili", "fertilizer_intensity"), ("grazing", "grazing_pressure"),
                        ("fragment", "fragmentation_level"), ("monocultur", "land_use_class"),
                        ("drought", "drought_frequency"), ("rain", "rainfall_pattern"), ("hedge", "field_margin_present"),
                        ("heat", "mean_temp_c"), ("temperature", "mean_temp_c")]:
            if kw in t:
                out["user_hypothesis"] = var
                break

    return {k: v for k, v in out.items() if v is not None}


INTERVENTION_KEYWORDS = {
    "broad_bed_furrow": ["broad bed", "broadbed", "bbf"],
    "in_situ_moisture_conservation": ["contour bund", "contour", "conservation furrow", "bunding", "water harvest"],
    "residue_retention": ["residue", "stubble", "straw"],
    "mulching": ["mulch"],
    "reduced_tillage": ["no-till", "no till", "zero till", "reduced tillage", "minimum tillage",
                        "conservation agriculture"],
    "farmyard_manure": ["farmyard manure", "fym", "manure", "compost", "organic amendment"],
    "cover_cropping": ["cover crop", "cover-crop", "green manure"],
    "legume_intercropping": ["legume", "intercrop", "pigeonpea", "pulse"],
    "crop_diversification": ["rotation", "diversif", "mixed crop"],
    "agroforestry": ["agroforestry", "tree", "alley cropping"],
    "field_margin_restoration": ["field margin", "hedgerow", "hedge", "flower strip", "border strip"],
    "habitat_connectivity": ["corridor", "connectivity", "patch connect"],
    "pesticide_reduction_ipm": ["ipm", "integrated pest", "pesticide", "insecticide", "spray"],
    "organic_management": ["organic farming", "organic management", "go organic"],
    "grazing_management": ["grazing", "livestock"],
}


QUESTION_CUES = ("what about", "how about", "should i", "should we", "would ", "could ", "can i", "can we",
                 "is it worth", "do you recommend", "any use", "what if")
# Values that name an intervention rather than a fact about the site.
INTERVENTION_VALUES = {"land_use_class": {"agroforestry": "agroforestry", "mixed_cropping": "legume_intercropping"}}


def is_question(text: str) -> bool:
    t = text.lower().strip()
    return t.endswith("?") or any(c in t for c in QUESTION_CUES)


def drop_question_artifacts(fields: dict, text: str) -> dict:
    """"What about agroforestry?" asks about an intervention; it does not say the land IS agroforestry."""
    if not is_question(text):
        return fields
    asked = set(asked_about(text))
    out = dict(fields)
    for field, mapping in INTERVENTION_VALUES.items():
        value = out.get(field)
        if value in mapping and mapping[value] in asked:
            del out[field]
    return out


def asked_about(text: str) -> list[str]:
    """Interventions the user named, longest keyword first so 'broad bed furrow' beats 'furrow'."""
    t = text.lower()
    found = []
    for intervention, keywords in INTERVENTION_KEYWORDS.items():
        if any(k in t for k in keywords):
            found.append(intervention)
    return found


# --------------------------------------------------------------------------- LLM (JSON mode)
def _schema() -> dict:
    props = {}
    for name in EXTRACTABLE:
        field = SiteState.model_fields.get(name)
        if name == "concern":
            props[name] = {"type": "STRING", "enum": CONCERNS, "nullable": True}
            continue
        if name == "user_hypothesis":
            props[name] = {"type": "STRING", "enum": HYPOTHESIS_VARIABLES, "nullable": True}
            continue
        ann = field.annotation
        args = [a for a in get_args(ann) if a is not type(None)]
        inner = args[0] if args else ann
        literals = get_args(inner)
        if literals and all(isinstance(x, str) for x in literals):
            props[name] = {"type": "STRING", "enum": list(literals), "nullable": True}
        elif inner is bool:
            props[name] = {"type": "BOOLEAN", "nullable": True}
        elif inner is float:
            props[name] = {"type": "NUMBER", "nullable": True}
        else:
            props[name] = {"type": "STRING", "nullable": True}
    return {"type": "OBJECT", "properties": props}


EXTRACT_SYSTEM = """You convert a farmer's or scientist's message into structured site data.
Rules:
- Fill a field ONLY if the message explicitly states it. Otherwise return null. Never guess, infer or use typical values.
- Do not convert vague words into numbers ("dry soil" is NOT a moisture value).
- soc_percent, moisture_percent are percentages; annual_rainfall_mm in mm; mean_temp_c in Celsius.
- user_hypothesis: only if the user states what they believe causes the problem.
- concern: the outcome they are worried about, if stated.
Return JSON only."""


def llm_extract(text: str, llm: LLMService) -> dict:
    raw = llm.generate_json(EXTRACT_SYSTEM, text, _schema())
    clean = {}
    for k, v in raw.items():
        if k not in EXTRACTABLE or v is None or v == "":
            continue
        try:
            SiteState(**{k: v})  # type/enum validation per field
            clean[k] = v
        except ValidationError:
            continue
    return clean


def extract(text: str, llm: LLMService) -> tuple[dict, str]:
    """Returns (fields, mode). mode is 'llm' or 'rules'."""
    if llm.enabled:
        try:
            return drop_question_artifacts(llm_extract(text, llm), text), "llm"
        except LLMError:
            pass
    return drop_question_artifacts(rule_extract(text), text), "rules"
