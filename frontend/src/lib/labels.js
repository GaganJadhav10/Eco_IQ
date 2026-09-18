// Display names only. No scientific content lives in the frontend.
export const VARIABLES = {
  soc_percent: { label: "Soil organic carbon", unit: "%", group: "Soil" },
  ph: { label: "Soil pH", unit: "", group: "Soil" },
  moisture_percent: { label: "Soil moisture", unit: "%", group: "Soil" },
  texture_class: { label: "Soil texture", group: "Soil", options: ["sandy", "loamy", "clayey", "vertisol"] },
  annual_rainfall_mm: { label: "Annual rainfall", unit: "mm", group: "Climate" },
  rainfall_pattern: { label: "Rainfall pattern", group: "Climate", options: ["normal", "low", "erratic"] },
  mean_temp_c: { label: "Mean temperature", unit: "°C", group: "Climate" },
  drought_frequency: { label: "Drought frequency", group: "Climate", options: ["low", "moderate", "high"] },
  land_use_class: { label: "Land use", group: "Land", options: ["monoculture", "mixed_cropping", "agroforestry", "grassland", "fallow"] },
  crop_system: { label: "Main crop", group: "Land", text: true },
  cropping_intensity: { label: "Cropping intensity", group: "Land", options: ["single", "double", "continuous"] },
  field_margin_present: { label: "Field margins / hedges", group: "Land", bool: true },
  species_richness_index: { label: "Species richness", unit: "spp.", group: "Biodiversity" },
  habitat_diversity_index: { label: "Habitat diversity", unit: "0–1", group: "Biodiversity" },
  pollinator_observed: { label: "Pollinator activity", group: "Biodiversity", options: ["none", "low", "moderate", "high"] },
  ndvi_proxy: { label: "Vegetation greenness (NDVI)", unit: "0–1", group: "Biodiversity" },
  fertilizer_intensity: { label: "Fertilizer use", group: "Human impact", options: ["low", "moderate", "high"] },
  pesticide_intensity: { label: "Pesticide use", group: "Human impact", options: ["low", "moderate", "high"] },
  grazing_pressure: { label: "Grazing pressure", group: "Human impact", options: ["none", "low", "moderate", "high"] },
  fragmentation_level: { label: "Habitat fragmentation", group: "Human impact", options: ["low", "moderate", "high"] },
  climate_zone: { label: "Climate zone", group: "Derived" },
};

export const GROUPS = ["Soil", "Climate", "Land", "Biodiversity", "Human impact"];

export const CONCERNS = {
  biodiversity_decline: "Biodiversity decline",
  pollinator_decline: "Pollinator decline",
  soil_degradation: "Soil degradation",
  vegetation_decline: "Vegetation decline",
};

export const INTERVENTIONS = {
  residue_retention: "Crop residue retention",
  mulching: "Mulching",
  in_situ_moisture_conservation: "Contour bunds & conservation furrows",
  broad_bed_furrow: "Broad bed & furrow",
  reduced_tillage: "Reduced tillage",
  farmyard_manure: "Farmyard manure",
  cover_cropping: "Cover cropping",
  legume_intercropping: "Legume intercropping",
  crop_diversification: "Crop diversification",
  agroforestry: "Agroforestry",
  field_margin_restoration: "Field margin restoration",
  habitat_connectivity: "Habitat connectivity",
  pesticide_reduction_ipm: "Integrated pest management",
  organic_management: "Organic management",
  grazing_management: "Grazing management",
};

export const STAGES = {
  relieve_limiting_constraint: { label: "Relieve the limiting constraint", short: "First", tone: "forest" },
  act_on_ranked_drivers: { label: "Act on ranked drivers", short: "Then", tone: "leaf" },
  defer_until_water_constraint_relieved: { label: "Deferred until water is secured", short: "Later", tone: "ochre" },
};

export const EVIDENCE = {
  meta_analysis: "Meta-analysis",
  multi_site: "Multi-site",
  single_site: "Single site",
  modelled: "Modelled",
};

export const SOURCE_LABEL = {
  json: "form / JSON",
  user_text: "your message",
  history: "site record",
  geo_lookup: "coordinates",
  derived: "derived",
};

export const varLabel = (v) => VARIABLES[v]?.label || humanize(v);
export const intLabel = (i) => INTERVENTIONS[i] || humanize(i);
export function humanize(s = "") {
  const t = String(s).replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
