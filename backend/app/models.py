"""Pydantic contracts. Assessment is the authoritative object (CLAUDE.md 3.1).

Nothing downstream (narrator, report, frontend) may read anything except these.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Frozen variable set (CLAUDE.md 2.1). Changing this list is a design change.
# ---------------------------------------------------------------------------
TextureClass = Literal["sandy", "loamy", "clayey", "vertisol"]
RainfallPattern = Literal["normal", "low", "erratic"]
Level3 = Literal["low", "moderate", "high"]
Level4 = Literal["none", "low", "moderate", "high"]
LandUse = Literal["monoculture", "mixed_cropping", "agroforestry", "grassland", "fallow"]
Intensity = Literal["single", "double", "continuous"]
ClimateZone = Literal["semi_arid", "sub_humid", "humid"]

NUMERIC_VARIABLES = [
    "soc_percent", "ph", "moisture_percent", "annual_rainfall_mm", "mean_temp_c",
    "species_richness_index", "habitat_diversity_index", "ndvi_proxy",
]
ENUM_VARIABLES = [
    "texture_class", "rainfall_pattern", "drought_frequency", "land_use_class",
    "cropping_intensity", "field_margin_present", "pollinator_observed",
    "fertilizer_intensity", "pesticide_intensity", "grazing_pressure",
    "fragmentation_level",
]
# Variables without which the diagnosis engine refuses to run (demo site 4).
CRITICAL_VARIABLES = [
    "soc_percent", "annual_rainfall_mm", "land_use_class", "texture_class",
    "habitat_diversity_index",
]

FieldSource = Literal["json", "user_text", "history", "geo_lookup", "derived"]


class SiteState(BaseModel):
    site_id: str = "adhoc"
    name: str | None = None
    lat: float | None = None
    lon: float | None = None
    concern: str | None = Field(None, description="Outcome the user cares about, e.g. biodiversity_decline")
    user_hypothesis: str | None = Field(None, description="Variable the user believes is the cause")

    # Soil
    soc_percent: float | None = None
    ph: float | None = None
    moisture_percent: float | None = None
    texture_class: TextureClass | None = None
    # Climate
    annual_rainfall_mm: float | None = None
    rainfall_pattern: RainfallPattern | None = None
    mean_temp_c: float | None = None
    drought_frequency: Level3 | None = None
    # Land
    land_use_class: LandUse | None = None
    crop_system: str | None = None
    cropping_intensity: Intensity | None = None
    field_margin_present: bool | None = None
    # Biodiversity
    species_richness_index: float | None = None
    habitat_diversity_index: float | None = None
    pollinator_observed: Level4 | None = None
    ndvi_proxy: float | None = None
    # Human impact
    fertilizer_intensity: Level3 | None = None
    pesticide_intensity: Level3 | None = None
    grazing_pressure: Level4 | None = None
    fragmentation_level: Level3 | None = None
    # Derived
    climate_zone: ClimateZone | None = None

    field_sources: dict[str, FieldSource] = Field(default_factory=dict)

    def known(self, var: str) -> bool:
        return getattr(self, var, None) is not None


class Measurement(BaseModel):
    site_id: str
    variable: str
    value: float
    date: str  # ISO date


# ---------------------------------------------------------------------------
# Knowledge base rows
# ---------------------------------------------------------------------------
class Source(BaseModel):
    id: str
    title: str
    publisher: str
    year: int
    region: str | None = None
    url: str | None = None


class Claim(BaseModel):
    id: str
    intervention: str
    target_metric: str
    direction: Literal["increase", "decrease"]
    effect_min: float | None = None
    effect_max: float | None = None
    effect_unit: str | None = None
    time_horizon: Literal["short", "medium", "long"]
    mechanism: str
    ctx_climate_zone: list[str] = []
    ctx_rainfall_min: float | None = None
    ctx_rainfall_max: float | None = None
    ctx_soil_texture: list[str] = []
    ctx_system: list[str] = []
    critical_dimensions: list[str] = []
    evidence_strength: Literal["meta_analysis", "multi_site", "single_site", "modelled"]
    source_id: str
    page: int | None = None
    quote: str | None = None
    verified: bool = False


class Relationship(BaseModel):
    """Conditional causal edge: a POOR state of from_variable degrades to_variable."""
    id: str
    from_variable: str
    to_variable: str
    weight: float  # 0-1 strength of the pathway as described in the source
    ctx_climate_zone: list[str] = []
    ctx_soil_texture: list[str] = []
    mechanism: str
    source_id: str
    verified: bool = False


class Intervention(BaseModel):
    """Properties of an intervention that drive sequencing, each with a source."""
    id: str
    label: str
    category: str                 # water_conservation | soil_carbon | diversification | input_reduction | grazing | connectivity
    competes_for_water: bool      # establishes new biomass that draws on scarce soil water before paying back
    addresses_variable: str | None = None  # pressure it removes; skipped when that pressure is absent
    note: str
    source_id: str


class Threshold(BaseModel):
    """Suitability cut-offs for a variable, conditioned on zone/texture ('*' = any)."""
    variable: str
    climate_zone: str = "*"
    texture_class: str = "*"
    poor: float | None = None      # numeric: value at which suitability = 0
    good: float | None = None      # numeric: value at which suitability = 1
    enum_scores: dict[str, float] = {}  # enum/bool variables
    source_id: str
    note: str


# ---------------------------------------------------------------------------
# The Assessment contract (CLAUDE.md 3.1)
# ---------------------------------------------------------------------------
class Driver(BaseModel):
    variable: str
    suitability_score: float
    supports_concern: bool
    temporal_trend: str | None
    assumption: str
    path_support: float = 0.0
    rank_score: float = 0.0
    path: list[str] = []
    source_ids: list[str] = []


class ClaimMatch(BaseModel):
    claim_id: str
    intervention: str
    target_metric: str
    direction: str
    effect_min: float | None
    effect_max: float | None
    effect_unit: str | None
    time_horizon: str
    context_match_score: float
    context_flags: list[str]
    disqualified: bool
    disqualify_reason: str | None
    evidence_strength: str
    source_id: str
    source_title: str
    page: int | None
    mechanism: str = ""
    verified: bool = False


class ConfidenceBreakdown(BaseModel):
    level: str
    n_supporting_claims: int
    context_quality_mean: float
    data_completeness: float
    n_conflicts: int
    rationale: list[str] = []


class MetricTarget(BaseModel):
    """A measurable goal for one metric, computed from the thresholds table (never invented)."""
    variable: str
    current: float | str | None
    target: float | str
    unit: str | None = None
    source_id: str
    note: str


class EvidenceEffect(BaseModel):
    """A quantified effect size carried by a supporting claim."""
    claim_id: str
    target_metric: str
    effect_min: float
    effect_max: float
    effect_unit: str | None
    time_horizon: str
    verified: bool
    context_match_score: float


class SequenceStep(BaseModel):
    order: int
    intervention: str
    stage: str               # "relieve_limiting_constraint" | "build_on_relief" | ...
    rationale: str
    target_metrics: list[str]
    time_horizon: str
    claim_ids: list[str]
    metric_targets: list[MetricTarget] = []
    evidence_effects: list[EvidenceEffect] = []


class Assessment(BaseModel):
    site_id: str
    status: Literal["complete", "insufficient_data"]
    suitability: dict[str, float] = {}
    limiting_factor: str | None
    drivers_ranked: list[Driver]
    under_determined: bool = False
    discriminating_measurement: str | None
    hypothesis_note: str | None = None
    eligible_claims: list[ClaimMatch]
    rejected_claims: list[ClaimMatch]
    recommended_sequence: list[str]
    sequence_detail: list[SequenceStep] = []
    confidence: ConfidenceBreakdown
    transfer_warnings: list[str]
    missing_variables: list[str]
    missing_variable_impact: dict[str, str] = {}
    # Mechanism passages retrieved by semantic search per recommended intervention. Context only:
    # retrieval never selects or orders a recommendation.
    supporting_passages: dict[str, list[dict]] = {}
