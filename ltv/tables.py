"""
The report's tables.

Like the figures, these are built from the model rather than typed, so they
move when the model moves and no agency can be left out by accident.

Each builder returns (head, rows) ready for `report._table`. `build(m)` returns
them in the order they appear in the report; `report.py` matches them to the
narrative's own tables by their header row, and leaves the written table in
place if the two ever drift apart.
"""
import numpy as np

from . import config as C
from .model import Model

# The gift amounts the per-agency tables show. Narrower than the full set
# because the columns either side carry too few donors to be worth a number.
AGENCY_BANDS = ["€5", "€8", "€10", "€12–13", "€15", "€20", "€25", "€30"]
# "Other" is a pooled catch-all, not a price point, so it is kept out of the
# tables as well as the charts. It remains inside the headline totals.
DASH = "—"


def _cap_label(agency: str) -> str:
    return "%s (%s)" % (agency, "capped" if agency in C.FEE_CAP else "no cap")


def _pct(v: float) -> str:
    if v <= 0:
        return "0%"
    return ("%.1f%%" % v) if v < 1 else ("%.0f%%" % v)


def _money(v) -> str:
    if v is None or not np.isfinite(v):
        return DASH
    return "€" + format(int(round(v)), ",d")


# ------------------------------------------------- 1 · gift mix by agency ---
def gift_mix(m: Model):
    head = ["Agency"] + list(C.CHART_ORDER)
    rows = []
    for agency in m.cost_table.index:
        share = m.band_share(agency)
        # Bold the amounts an agency actually concentrates on, so the shape of
        # each agency's book is readable at a glance.
        cells = []
        for b in C.CHART_ORDER:
            v = share.get(b, 0.0)
            cells.append("<b>%s</b>" % _pct(v) if v >= C.MAIN_BAND_SHARE else _pct(v))
        rows.append([_cap_label(agency)] + cells)
    return head, rows


# ---------------------------------------------- 2 · average age by amount ---
def age_by_amount(m: Model):
    """Average age of the donors each agency recruits, across all gift amounts."""
    head = ["Agency", "Average age at sign-up"]
    cohort = m.cohort[m.cohort["agency"].notna()]
    rows = []
    for agency in m.cost_table.index:
        ages = cohort[cohort["agency"] == agency]["age"].dropna()
        rows.append([agency, "%d" % round(ages.mean()) if len(ages) else DASH])
    allages = cohort["age"].dropna()
    rows.append(["All agencies",
                 "%d" % round(allages.mean()) if len(allages) else DASH])
    return head, rows


# ------------------------------------------- 3 · gross LTV by agency x ask --
def gross_by_amount(m: Model):
    head = ["Agency"] + AGENCY_BANDS
    rows = []
    for agency in m.cost_table.index:
        share = m.band_share(agency)
        profile = m.age_profile(agency)
        row = [agency]
        for band in AGENCY_BANDS:
            value = (m.gross_ltv_profile(band, profile)
                     if share.get(band, 0.0) >= C.MIN_SHARE else None)
            row.append(_money(value))
        rows.append(row)
    return head, rows


# ------------------------------------------------- 4 · the agency summary ---
def agency_summary(m: Model):
    head = ["Agency", "2026 donors", "Avg monthly gift", "Avg CPA", "CPA factor"]
    summary = m.agency_summary()
    cohort = m.cohort[m.cohort["agency"].notna()]
    rows = []
    donors = cost = net = 0.0
    for agency in m.cost_table.index:
        if agency not in summary.index:
            continue
        n = float(summary.loc[agency, "donors"])
        gift = cohort[cohort["agency"] == agency]["monthly"].mean()
        rows.append([
            _cap_label(agency),
            format(int(round(n)), ",d"),
            _money(gift),
            _money(summary.loc[agency, "avg_cpa"]),
            "×%.2f" % float(m.cost_table.loc[agency, "cpa_factor"]),
        ])
        donors += n
        cost += float(summary.loc[agency, "cost"])
        net += float(summary.loc[agency, "net_income"])
    rows.append([
        "All agencies", format(int(round(donors)), ",d"),
        _money(cohort["monthly"].mean()),
        _money(cost / donors if donors else np.nan), DASH,
    ])
    return head, rows


# ------------------------------------------------ 5 · upgrades by amount ----
def upgrades(m: Model):
    head = ["Monthly gift", "Upgraded", "Average increase", "Downgraded"]
    behaviour = m._behaviour_frame()
    rows = []
    for band in C.CHART_ORDER:
        sub = behaviour[behaviour["band"] == band]
        if len(sub) < C.MIN_CELL:
            continue
        moved = sub["LatestGiftAmount_MonthlyEquiv"] - sub["FirstGiftAmount_MonthlyEquiv"]
        down = float((moved < -0.01).mean()) * 100
        rate, amount = m.upgrade_rates(band)
        rows.append([band, "%.1f%%" % (rate * 100), "€%.2f" % amount,
                     "%.1f%%" % down])
    return head, rows


# ------------------------------------------------------ 6, 7 · fee tables ---
def _fee_table(m: Model, column: str, label: str, blended: bool):
    head = ["Agency"] + list(C.CHART_ORDER)
    rows = []
    vols = m.volumes()
    for agency in m.cost_table.index:
        factor = float(m.cost_table.loc[agency, column])
        cap = C.FEE_CAP.get(agency)
        name = "%s (×%.2f%s)" % (agency, factor,
                                 ", capped" if cap else ", no cap") if label == "cpa" \
            else "%s (×%.2f)" % (agency, factor)
        row = [name]
        for band in C.CHART_ORDER:
            gift = m.band_gift(band)
            charged = min(gift, cap) if cap else gift
            row.append(_money(factor * charged))
        rows.append(row)
    if blended:
        row = ["Blended, as used in the model"]
        for band in C.CHART_ORDER:
            n = float(vols[band].sum()) if band in vols.columns else 0.0
            row.append(_money(m.blended_cpa(band)) if n > 0 else DASH)
        rows.append(row)
    return head, rows


def cpa_by_amount(m: Model):
    """What each agency charges for a donor, at each gift amount."""
    return _fee_table(m, "cpa_factor", "cpa", blended=True)


def cpsu_by_amount(m: Model):
    """The same on the sign-up factor, before drop-out between sign-up and
    first payment."""
    return _fee_table(m, "cpsu_factor", "cpsu", blended=False)


# ------------------------------------------- 8 · who recruits each age band -
def age_source(m: Model):
    head = ["Age at sign-up"] + list(m.cost_table.index)
    cohort = m.cohort[m.cohort["agency"].notna()]
    rows = []
    for ab in C.AGE_ORDER:
        sub = cohort[cohort["ab"] == ab]
        row = [ab]
        for agency in m.cost_table.index:
            row.append(_pct(100 * float((sub["agency"] == agency).mean())
                            if len(sub) else 0.0))
        rows.append(row)
    return head, rows


# ------------------------------------------------------------------ all -----
BUILDERS = [gift_mix, age_by_amount, gross_by_amount, agency_summary,
            upgrades, cpa_by_amount, cpsu_by_amount, age_source]


def build(m: Model) -> list:
    """Every table the report can draw, in the order it uses them."""
    out = []
    for fn in BUILDERS:
        try:
            out.append(fn(m))
        except Exception as exc:                      # pragma: no cover
            print("  table %s could not be built: %s" % (fn.__name__, exc))
            out.append(None)
    return out
