"""Temporal trend detection over dated measurements (CLAUDE.md 4.5). Pure functions."""
from __future__ import annotations

from datetime import date

from app.models import Measurement

MIN_POINTS = 2
RELATIVE_CHANGE_CUTOFF = 0.05  # |fitted change over period| / mean below this counts as stable


def trend(points: list[Measurement]) -> str | None:
    """Least-squares slope, expressed as relative change across the observed period."""
    pts = sorted(points, key=lambda m: m.date)
    if len(pts) < MIN_POINTS:
        return None
    xs = [(date.fromisoformat(str(m.date)) - date.fromisoformat(str(pts[0].date))).days for m in pts]
    ys = [m.value for m in pts]
    n = len(pts)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0 or my == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    rel = slope * (xs[-1] - xs[0]) / abs(my)
    if rel <= -RELATIVE_CHANGE_CUTOFF:
        return "declining"
    if rel >= RELATIVE_CHANGE_CUTOFF:
        return "improving"
    return "stable"


def trends_by_variable(measurements: list[Measurement]) -> dict[str, str]:
    grouped: dict[str, list[Measurement]] = {}
    for m in measurements:
        grouped.setdefault(m.variable, []).append(m)
    out = {}
    for var, pts in grouped.items():
        t = trend(pts)
        if t is not None:
            out[var] = t
    return out


def trend_factor(driver_trend: str | None, outcome_trend: str | None) -> float:
    """Multiplier on a driver's rank. Co-declining with the outcome strengthens it;
    a driver that is improving while the outcome declines is a weaker explanation."""
    if driver_trend is None or outcome_trend != "declining":
        return 1.0
    return {"declining": 1.25, "stable": 0.85, "improving": 0.6}[driver_trend]
