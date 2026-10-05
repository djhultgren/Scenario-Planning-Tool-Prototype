"""
Checks that the model is telling the truth.

Three kinds:

  reconcile()   - do the rebuilt numbers match what was published?
  holdout()     - does the projection method work on years we can verify?
  sensitivity() - which conclusions survive when the assumptions are wrong?
  precision()   - how much does each estimate move on the sample we happen
                  to have?

Run `python -m ltv.validate` to print all four.
"""
import numpy as np
import pandas as pd

from . import config as C
from . import survival as S
from .model import Model

# 12-month retention as published in the v27 report, by gift band.
PUBLISHED_R12 = {
    "€5": 80, "€8": 68, "€10": 60, "€12–13": 57,
    "€15": 54, "€20": 56, "€25": 49, "€30": 52,
}
# Ten-year gross LTV as published, by gift band.
PUBLISHED_GROSS = {
    "€5": 362, "€8": 484, "€10": 607, "€12–13": 604,
    "€15": 750, "€20": 1071, "€25": 1034, "€30": 1280,
}
# Agency CPA factors as published.
PUBLISHED_CPA_FACTOR = {
    "Trust": 19.97, "Apollon": 24.01, "Activate": 20.86, "Wesser": 29.65,
}


def reconcile(m: Model) -> pd.DataFrame:
    """Rebuilt figures against the published report, band by band."""
    rows = []
    b = m.band_summary()
    for band, pub in PUBLISHED_R12.items():
        rates = m.band_rates.get(band)
        if rates is None:
            continue
        got_r12 = 100 * rates["R12"]
        got_ltv = b["gross_ltv"].get(band, np.nan)
        pub_ltv = PUBLISHED_GROSS[band]
        rows.append({
            "band": band,
            "r12_model": round(got_r12, 1),
            "r12_report": pub,
            "r12_diff": round(got_r12 - pub, 1),
            "ltv_model": round(float(got_ltv), 0) if np.isfinite(got_ltv) else None,
            "ltv_report": pub_ltv,
            "ltv_diff_pct": (round(100 * (got_ltv - pub_ltv) / pub_ltv, 1)
                             if np.isfinite(got_ltv) else None),
            "historic_n": rates["n"],
        })
    return pd.DataFrame(rows).set_index("band")


def holdout(m: Model) -> pd.DataFrame:
    """
    Hide years 4 and 5, refit on years 1-3, then predict them back.

    This is the test that shows the projection works on real donors over a
    stretch we can actually check.
    """
    rows = []
    for ab in C.AGE_ORDER:
        rates = m.band_rates.get("€10")
        cell = m.cells.get(("€10", ab)) or rates
        if cell is None:
            continue
        t = m.tail[ab]
        m36 = cell["R24"] * t[3]
        m48, m60 = m36 * t[4], m36 * t[4] * t[5]
        actual = [cell["R12"], cell["R24"], m36, m48, m60]

        predicted = S.project_annual(actual[:3], 5)
        rows.append({
            "age_band": ab,
            "y4_actual": round(100 * actual[3], 1),
            "y4_predicted": round(100 * predicted[3], 1),
            "y4_error_pts": round(100 * (predicted[3] - actual[3]), 1),
            "y5_actual": round(100 * actual[4], 1),
            "y5_predicted": round(100 * predicted[4], 1),
            "y5_error_pts": round(100 * (predicted[4] - actual[4]), 1),
        })
    return pd.DataFrame(rows).set_index("age_band")


# ------------------------------------------------------------ sensitivity ---
SCENARIOS = {
    "Base": {},
    "Tail years 3-5 -10%": {"tail_mult": 0.90},
    "Tail years 3-5 -20%": {"tail_mult": 0.80},
    "Years 6-10 -10%": {"proj_mult": 0.90},
    "Years 6-10 -20%": {"proj_mult": 0.80},
    "Upgrades halved": {"upgrade_mult": 0.5},
    "No upgrades": {"upgrade_mult": 0.0},
    "Mortality applied": {"mortality": True},
    "Discounted 3.5% real": {"discount": 0.035},
    "Mortality + discount + tail -10%": {
        "mortality": True, "discount": 0.035, "tail_mult": 0.90},
    "Five-year horizon": {"months": 60},
}

# Annual mortality by age band, approximate German period life table.
MORTALITY = {"18–29": 0.0006, "30–39": 0.0012, "40–49": 0.0030,
             "50–64": 0.0080, "65+": 0.0350}


def _stressed_ltv(m: Model, band: str, ab: str, months=C.HORIZON_MONTHS,
                  tail_mult=1.0, proj_mult=1.0, upgrade_mult=1.0,
                  mortality=False, discount=0.0) -> float | None:
    rates = m.cells.get((band, ab)) or m.band_rates.get(band)
    if rates is None:
        return None
    t = m.tail[ab]
    m36 = rates["R24"] * min(t[3] * tail_mult, 0.999)
    m48 = m36 * min(t[4] * tail_mult, 0.999)
    m60 = m48 * min(t[5] * tail_mult, 0.999)
    annual = [rates["R12"], rates["R24"], m36, m48, m60]
    projected = S.project_annual(annual, C.HORIZON_MONTHS // 12)
    if proj_mult != 1.0:
        projected = annual + [v * (proj_mult ** (i + 1))
                              for i, v in enumerate(projected[5:])]

    anchors = [(0, 1.0), (3, rates["R3"])]
    for i, v in enumerate(projected, start=1):
        anchors.append((12 * i, v))
    curve = S.curve_from_anchors(anchors, C.HORIZON_MONTHS)

    if mortality:
        mu = MORTALITY[ab]
        curve = curve * np.array([(1 - mu) ** (i / 12.0) for i in range(len(curve))])
    disc = (np.array([1.0 / ((1 + discount) ** (i / 12.0)) for i in range(len(curve))])
            if discount else np.ones(len(curve)))

    year_one = S.annuity(curve, 1, 12)
    if year_one <= 0:
        return None
    monthly = rates["LTV1"] / year_one
    cd = curve * disc
    return float(monthly * S.annuity(cd, 1, months)
                 + rates["upgrade_rate"] * rates["upgrade_amt"] * upgrade_mult
                 * S.annuity(cd, 13, months))


def sensitivity(m: Model) -> pd.DataFrame:
    """Re-run the model under each stress and report what changes."""
    vols = m.volumes()
    thick = ["€10", "€12–13", "€15", "€20"]
    rows = []
    for name, kw in SCENARIOS.items():
        nets, total = {}, 0.0
        for band in C.BAND_ORDER:
            profile = m.age_profile(band=band)
            num = den = 0.0
            for ab, w in profile.items():
                v = _stressed_ltv(m, band, ab, **kw)
                if v is None:
                    continue
                num += w * v
                den += w
            if den == 0:
                continue
            ltv = num / den
            n = float(vols[band].sum())
            fee = (sum(float(vols.loc[a, band]) * m.cpa(a, band)
                       for a in vols.index if np.isfinite(m.cpa(a, band))) / n
                   if n else 0.0)
            nets[band] = ltv - fee
            total += n * (ltv - fee)
        best = max((b for b in thick if b in nets), key=lambda b: nets[b])
        row = {"scenario": name, "best_band": best,
               "net_income": round(total, 0)}
        row.update({b: round(nets.get(b, np.nan), 0) for b in C.BAND_ORDER})
        rows.append(row)
    return pd.DataFrame(rows).set_index("scenario")


def precision(m: Model, draws: int = 300, seed: int = 7) -> pd.DataFrame:
    """
    Bootstrap each gift band to see how firm its estimate is.

    Resamples the historic donors in the band with replacement and recomputes
    12-month retention and first-year value, which together drive the LTV.
    """
    rng = np.random.default_rng(seed)
    b = m._behaviour_frame()
    rows = []
    for band in C.BAND_ORDER:
        sub = b[b["band"] == band]
        n = len(sub)
        if n < C.MIN_CELL:
            continue
        r12 = sub["RetainedMonth12"].to_numpy(dtype=float)
        ltv1 = sub["LTV_1yr_Local"].to_numpy(dtype=float)
        stats = []
        for _ in range(draws):
            idx = rng.integers(0, n, n)
            stats.append(np.nanmean(r12[idx]) * np.nanmean(ltv1[idx]))
        lo, hi = np.percentile(stats, [5, 95])
        mid = np.nanmean(r12) * np.nanmean(ltv1)
        rows.append({
            "band": band, "historic_n": n,
            "interval_pct": round(100 * (hi - lo) / mid, 1) if mid else np.nan,
            "confidence": ("high" if n >= 3000 else
                           "moderate" if n >= 500 else "low"),
        })
    return pd.DataFrame(rows).set_index("band")


def main():
    pd.set_option("display.width", 220)
    m = Model.build()
    print("=" * 78, "\nRECONCILIATION against the published v27 report\n", "=" * 78)
    print(reconcile(m).to_string())
    print("\n", "=" * 78, "\nHOLDOUT: refit on years 1-3, predict years 4-5\n", "=" * 78)
    print(holdout(m).to_string())
    print("\n", "=" * 78, "\nSENSITIVITY\n", "=" * 78)
    s = sensitivity(m)
    print(s[["best_band", "net_income", "€10", "€15", "€20"]].to_string())
    print("\nBest band in every scenario:", sorted(set(s["best_band"])))
    print("Net income range: %.2fm to %.2fm" %
          (s["net_income"].min() / 1e6, s["net_income"].max() / 1e6))
    print("\n", "=" * 78, "\nPRECISION (bootstrap)\n", "=" * 78)
    print(precision(m).to_string())


if __name__ == "__main__":
    main()
