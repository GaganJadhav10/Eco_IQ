"""Climate zone derivation from rainfall when coordinates are absent. Pure function.

Bands follow the moisture-regime boundaries used in the NBSS&LUP agro-ecological
region map of India (source id: nbss_aer_1992). The arid band (<500 mm) is folded
into semi_arid because arid systems are outside this project's scope (CLAUDE.md 2).
"""
from __future__ import annotations

ZONE_SOURCE_ID = "nbss_aer_1992"
SEMI_ARID_MAX_MM = 1000.0
SUB_HUMID_MAX_MM = 1500.0


def zone_from_rainfall(rainfall_mm: float | None) -> str | None:
    if rainfall_mm is None:
        return None
    if rainfall_mm < SEMI_ARID_MAX_MM:
        return "semi_arid"
    if rainfall_mm < SUB_HUMID_MAX_MM:
        return "sub_humid"
    return "humid"
