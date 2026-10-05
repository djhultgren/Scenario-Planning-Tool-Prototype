"""
The scenario planner.

Builds a 2026 acquisition plan, applies optimisation levers, and compares
saved scenarios against the baseline. Generated as one self-contained HTML
file with the model output embedded, so it works offline.

Everything the page shows is read from the model rather than recomputed here,
so the planner's opening position - before any lever is touched - reproduces
the report's headline figures exactly. The planner works in wider bands than
the report, because a plan moves blocks of donors rather than setting exact
asks, so each planner band is the volume-weighted aggregate of the report
bands that fall inside it.

This module's job is to compute the payload; the page's behaviour lives in
`planner_template.html`.
"""
import json
from pathlib import Path

import numpy as np

from . import config as C
from .model import Model


# --------------------------------------------------------------- payload ---
def _band_of(monthly: float) -> str | None:
    """Which planner band a monthly gift falls in."""
    if monthly is None or not np.isfinite(monthly):
        return None
    for label, lo, hi in C.PLANNER_BANDS:
        if lo <= monthly < hi:
            return label
    # Above the top band: price it in the top band rather than lose the donor.
    return C.PLANNER_BANDS[-1][0] if monthly >= C.PLANNER_BANDS[-1][2] else None


def _split(m: Model) -> dict:
    """
    Report-band volumes distributed across the planner's wider bands.

    Returns {planner band: {(agency, report band): donors}}. The donor counts
    are the model's own - `Model.volumes()`, scaled to the realised-donor
    counts in the cost file and annualised - so they add up to the report's
    total. The split within each cell follows the gift amounts the 2026 cohort
    actually gave.
    """
    vols = m.volumes()
    cohort = m.cohort[m.cohort["agency"].notna()].copy()
    cohort["pb"] = cohort["monthly"].apply(_band_of)

    out: dict[str, dict[tuple[str, str], float]] = {
        label: {} for label, _, _ in C.PLANNER_BANDS}
    for agency in vols.index:
        for band in C.BAND_ORDER:
            n = float(vols.loc[agency, band]) if band in vols.columns else 0.0
            if n <= 0:
                continue
            sub = cohort[(cohort["agency"] == agency) & (cohort["band"] == band)]
            shares = sub["pb"].value_counts(normalize=True) if len(sub) else None
            if shares is None or shares.empty:
                pb = _band_of(m.band_gift(band))
                shares = {pb: 1.0} if pb else {}
            for pb, share in dict(shares).items():
                if pb in out and share > 0:
                    out[pb][(agency, band)] = out[pb].get((agency, band), 0.0) + n * share
    return out


def _aggregate(m: Model, parts: dict) -> dict | None:
    """
    Collapse a planner band's report-band parts into one set of figures.

    Survival, lifetime values and upgrade behaviour are volume-weighted across
    the report bands inside this planner band, each valued on the age profile
    it actually acquires. Weighting the lifetime values here - rather than
    rebuilding a curve from pooled retention and revaluing it - is what keeps
    the planner's baseline equal to the report.
    """
    total = sum(parts.values())
    if total <= 0:
        return None

    horizon = C.HORIZON_MONTHS
    curve = np.zeros(horizon + 1)
    ltv = {y: 0.0 for y in C.PLANNER_HORIZONS}
    uprate = upamt = gift = cw = lw = 0.0

    by_band: dict[str, float] = {}
    for (_, band), n in parts.items():
        by_band[band] = by_band.get(band, 0.0) + n

    for band, n in by_band.items():
        profile = m.age_profile(band=band)
        c = _band_curve(m, band, profile)
        if c is not None:
            curve += n * c
            cw += n
        vals = {y: m.gross_ltv_profile(band, profile, y * 12)
                for y in C.PLANNER_HORIZONS}
        if all(v is not None for v in vals.values()):
            for y, v in vals.items():
                ltv[y] += n * v
            rates = m.band_rates.get(band) or {}
            uprate += n * rates.get("upgrade_rate", 0.0)
            upamt += n * rates.get("upgrade_amt", 0.0)
            lw += n
        gift += n * m.band_gift(band)

    if cw <= 0 or lw <= 0:
        return None
    curve = curve / cw

    entry = {
        "S": [round(float(v), 6) for v in curve],
        "r3": float(curve[3]), "r12": float(curve[12]), "r24": float(curve[24]),
        "r36": float(curve[36]), "r48": float(curve[48]), "r60": float(curve[60]),
        "uprate": uprate / lw,
        "upamt": round(upamt / lw, 2),
        "fg": round(gift / total, 2),
        "vol": int(round(total)),
        # The joint distribution of agency and fee basis inside this band, so
        # the page can reprice it at any agency, cap level or cap setting and
        # still land on the model's figure when nothing is changed.
        "fee": [{"a": agency, "g": round(m.band_gift(band), 2),
                 "w": round(n / total, 6)}
                for (agency, band), n in sorted(parts.items())],
    }
    for y in C.PLANNER_HORIZONS:
        entry["ltv%d_obs" % y] = float(ltv[y] / lw)
    return entry


def _band_curve(m: Model, band: str, profile: dict[str, float]):
    """One report band's survival curve, weighted across its age profile."""
    total = np.zeros(C.HORIZON_MONTHS + 1)
    weight = 0.0
    for ab, w in profile.items():
        if w <= 0:
            continue
        c = m.curve(band, ab)
        if c is None:
            continue
        total += w * c
        weight += w
    return total / weight if weight > 0 else None


def payload(m: Model) -> dict:
    """Everything the planner page needs."""
    split = _split(m)

    bands, p = [], {}
    for label, _, _ in C.PLANNER_BANDS:
        entry = _aggregate(m, split.get(label, {}))
        if entry is None or entry["vol"] <= 0:
            continue
        bands.append(label)
        p[label] = entry

    attributed = m.cohort[m.cohort["agency"].notna()]
    agencies = [{
        "name": name,
        "factor": float(m.cost_table.loc[name, "cpa_factor"]),
        "share": round(float((attributed["agency"] == name).mean()), 4)
                 if len(attributed) else 0.0,
        "caps": name in C.FEE_CAP,
    } for name in m.cost_table.index]

    return {
        "bands": bands,
        "p": p,
        "agencies": agencies,
        "cap": C.DEFAULT_CAP,
        "horizons": C.PLANNER_HORIZONS,
        "horizon_default": max(C.PLANNER_HORIZONS),
        "months": C.HORIZON_MONTHS,
    }


# ------------------------------------------------------------------ page ---
TEMPLATE_FILE = Path(__file__).with_name("planner_template.html")


def build(m: Model, path=None) -> str:
    """Write the planner and return the path."""
    path = path or (C.OUT / "scenario_planner.html")
    html = TEMPLATE_FILE.read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(payload(m), ensure_ascii=False,
                                               default=float))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)
