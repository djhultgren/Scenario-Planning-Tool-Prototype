"""
The report's figures.

Each function here takes the model and returns finished HTML for one figure.
Where a figure has a slicer, every view is drawn up front and the page shows
one at a time - so the report needs no chart library, no network, and nothing
is recalculated in a reader's browser.

`build(m)` returns them keyed by figure number, which is how `report.py` slots
them into the narrative.
"""
import re

import numpy as np

from . import charts as G
from . import config as C
from . import survival as S
from .model import Model

AGE_KEYS = ["All"] + list(C.AGE_ORDER)

# Steps above the cap that Figure 9 prices. €25 is left out: it rests on 375
# historic donors with unusually low retention, so the step reads as a quirk of
# that sample rather than as anything about the price point.
CAP_STEPS = [30, 35, 40]


def _age_label(key: str) -> str:
    return "all donors" if key == "All" else "donors aged %s at sign-up" % key


def _age_note(key: str) -> str:
    if key == "All":
        return "All donors, each amount valued on the age profile it actually acquires."
    return ("Only donors who were %s when they signed up, so the comparison "
            "between amounts is like for like on age." % key)


# ------------------------------------------------- 1 · volumes by amount ----
def volumes(m: Model, bands) -> str:
    return G.volumes_by_band(bands)


# -------------------------------------------- 2 · what we have modelled ----
def behaviour(m: Model, bands) -> str:
    total = float(bands["donors"].sum())
    rows = []
    for band in C.CHART_ORDER:
        if band not in bands.index:
            continue
        # "Other" is a catch-all of high-value outliers rather than a price
        # point we could ask for, and its average upgrade is large enough to
        # flatten every other bar on that panel. The share percentages are
        # still taken against all donors, so the column does not add to 100.
        if band == "Other":
            continue
        curve = m.curve_at(band)
        uprate, upamt = m.upgrade_rates(band)
        rows.append({
            "band": band,
            "donors": float(bands.loc[band, "donors"]),
            "share": 100 * float(bands.loc[band, "donors"]) / total if total else 0.0,
            "age": m.mean_age(band),
            "r12": float(curve[12]) if curve is not None else 0.0,
            "uprate": uprate,
            "upamt": upamt,
        })
    return G.behaviour_panel(rows)


# ------------------------------------------ 3 · gross LTV, sliced by age ----
def _ltv_states(m: Model, net: bool) -> list:
    """Every age view of the lifetime-value bars, on one shared scale."""
    withheld = _schedule_driven(m)
    values, counts = {}, {}
    for key in AGE_KEYS:
        ab = None if key == "All" else key
        values[key] = {}
        counts[key] = {}
        for band in C.CHART_ORDER:
            if ab is not None and band in withheld:
                continue
            gross = m.gross_ltv_at(band, ab)
            if gross is None:
                continue
            fee = m.blended_cpa(band)
            if net and not np.isfinite(fee):
                continue
            values[key][band] = gross - fee if net else gross
            counts[key][band] = m.cell_n(band, ab)

    mx = max([v for d in values.values() for v in d.values()] + [1.0]) * 1.04
    what = "net" if net else "gross"
    tail = ("Net of a blended CPA across the %d agencies. Faded bars marked "
            "&ldquo;low base&rdquo; rest on fewer than %d historic donors."
            % (len(m.cost_table), C.LOW_BASE)) if net else (
           "Faded bars marked &ldquo;low base&rdquo; rest on fewer than %d "
           "historic donors and should be read as indicative." % C.LOW_BASE)

    states = []
    for key in AGE_KEYS:
        if not values[key]:
            continue
        note = "%s %s" % (_age_note(key), tail)
        if key != "All" and withheld:
            note += (" %s %s not shown by age: most of those donors pay annually "
                     "or quarterly, and the retention schedules behind them are a "
                     "single set of rates used at every age. That is sound across "
                     "all donors, so these bands appear in the <i>All</i> view, "
                     "but inside an age band it would report the assumption back "
                     "rather than what the donors did."
                     % (", ".join(withheld),
                        "are" if len(withheld) > 1 else "is"))
        states.append((
            key,
            "Donor %s LTV (10 years) - %s" % (what, _age_label(key)),
            G.ltv_bars(values[key], counts[key], mx, C.LOW_BASE,
                       bands=[b for b in C.CHART_ORDER
                              if not (key != "All" and b in withheld)]),
            note,
        ))
    return states


def gross_ltv(m: Model, bands) -> str:
    return G.sliced("gl", _ltv_states(m, net=False))


def net_ltv(m: Model, bands) -> str:
    return G.sliced("nl", _ltv_states(m, net=True))


# --------------------------------------------- 4 · value by age at signup ---
def by_age(m: Model, bands) -> str:
    """
    Value and retention by age, holding the ask at €10.

    Keeping the amount fixed is the point of the chart: it isolates age, so a
    reader cannot mistake the pattern for an effect of older donors being asked
    for more.
    """
    profile = m.age_profile()
    rows = []
    for ab in C.AGE_ORDER:
        share = profile.get(ab, 0.0)
        gross = m.gross_ltv_at("€10", ab)
        curve = m.curve_at("€10", ab)
        if share <= 0 or gross is None or curve is None:
            continue
        rows.append({"ab": ab, "share": share, "gross": gross,
                     "r12": float(curve[12])})
    return G.age_panel(rows)


# -------------------------------------------- 5 · retention, sliced by age --
def _schedule_driven(m: Model) -> list:
    """
    Bands whose retention is mostly set by the payment-frequency schedules.

    Those schedules are all-age averages, so they describe the whole donor base
    honestly but cannot be split by age. A band where most donors pay annually
    is therefore shown only in the all-ages view: in an age band it would be
    reporting the assumption back rather than anything measured.
    """
    out = []
    for band in C.CHART_ORDER:
        mix = m.frequency_mix(band)
        if 1.0 - mix.get("M", 0.0) > C.NON_MONTHLY_LIMIT:
            out.append(band)
    return out


def retention(m: Model, bands) -> str:
    states = []
    withheld = _schedule_driven(m)
    for key in AGE_KEYS:
        ab = None if key == "All" else key
        curves, counts = {}, {}
        for band in C.CHART_ORDER:
            if ab is not None and band in withheld:
                continue
            curve = m.curve_at(band, ab)
            if curve is None:
                continue
            curves[band] = curve
            counts[band] = m.cell_n(band, ab)
        if not curves:
            continue
        missing = [b for b in C.CHART_ORDER
                   if b in m.band_rates and b not in curves
                   and not (ab is not None and b in withheld)]
        note = ("Labels show 12-month retention &rarr; year-10 retention. Solid "
                "to month %d is observed; dashed beyond is projected."
                % C.OBSERVED_MONTHS)
        if key != "All":
            note += " Showing only donors who were %s when they signed up." % key
        if missing:
            note += (" %s %s not shown - too few donors in this age band."
                     % (", ".join(missing), "are" if len(missing) > 1 else "is"))
        if ab is not None and withheld:
            note += (" %s %s not shown by age: most of %s donors pay annually or "
                     "quarterly, and the retention schedules for those donors are "
                     "a single set of rates used at every age. They are reliable "
                     "across all donors, which is why these bands appear in the "
                     "<i>All</i> view, but they cannot tell us how a younger "
                     "annual donor differs from an older one."
                     % (", ".join(withheld),
                        "are" if len(withheld) > 1 else "is",
                        "their" if len(withheld) > 1 else "its"))
        states.append((
            key,
            "Retention by gift amount - %s" % _age_label(key),
            G.retention_lines(curves, counts, C.LOW_BASE),
            note,
        ))
    return G.sliced("rt", states)


# ------------------------------------ 6 · agency cost and value by amount ---
def agencies(m: Model, bands) -> str:
    names = list(m.cost_table.index)
    shares = {a: m.band_share(a) for a in names}
    vols = m.volumes()

    views = {}
    for key in ["All"] + list(C.CHART_ORDER):
        rows = []
        for agency in names:
            if key == "All":
                summary = m.agency_summary()
                if agency not in summary.index:
                    continue
                cpa = float(summary.loc[agency, "avg_cpa"])
                net = float(summary.loc[agency, "net_ltv"])
                donors = float(summary.loc[agency, "donors"])
                sub = "%s donors · ×%.2f%s" % (
                    format(int(round(donors)), ",d"),
                    float(m.cost_table.loc[agency, "cpa_factor"]),
                    " capped" if agency in C.FEE_CAP else "")
            else:
                share = shares[agency].get(key, 0.0)
                cpa = m.cpa(agency, key)
                if not np.isfinite(cpa):
                    continue
                if share < C.MIN_SHARE:
                    # Too few donors to say anything: leave the agency off the
                    # chart entirely rather than showing a cost with no value
                    # beside it.
                    continue
                net = m.agency_net(agency, key)
                sub = "%s%% of their donors · ×%.2f%s" % (
                    ("%.1f" % share) if share < 1 else ("%.0f" % round(share)),
                    float(m.cost_table.loc[agency, "cpa_factor"]),
                    " capped" if agency in C.FEE_CAP else "")
            rows.append((agency, cpa, net, sub))
        if rows:
            views[key] = rows

    mx = max([v for rows in views.values() for _, cpa, net, _ in rows
              for v in (cpa, net) if v is not None] + [1.0]) * 1.16

    states = []
    for key, rows in views.items():
        hidden = [a for a in names if a not in [r[0] for r in rows]]
        if key == "All":
            title = "CPA and 10-year net LTV by agency - all gift values"
            note = ("Each agency on its own fee rate, across every gift value "
                    "it acquires.")
        else:
            title = "CPA and 10-year net LTV by agency - donors giving %s" % key
            note = ("Each agency&rsquo;s own fee rate at %s, and what a donor at "
                    "that amount is worth to us net over ten years." % key)
        if hidden:
            note += (" %s %s not shown because %s fewer than %g%% of "
                     "%s donors at this amount."
                     % (", ".join(hidden),
                        "are" if len(hidden) > 1 else "is",
                        "they acquire" if len(hidden) > 1 else "it acquires",
                        C.MIN_SHARE, "their" if len(hidden) > 1 else "its"))
        states.append((key, title, G.agency_bars(rows, mx), note))
    return G.sliced("agn", states)


# ------------------------------------------------- 7 · net LTV (see above) --
# net_ltv is defined with gross_ltv, because they share a scale.


# ------------------------------------------------------- 8 · payback time ---
def _payback_months(m: Model, band: str, fee: float) -> tuple:
    """Months of giving before a donor has covered the fee, and the return."""
    curve = m.curve_at(band)
    gross = m.gross_ltv_at(band)
    if curve is None or gross is None or not np.isfinite(fee) or fee <= 0:
        return None, 0.0
    year_one = S.annuity(curve, 1, 12)
    if year_one <= 0:
        return None, 0.0
    rates = m.band_rates.get(band) or {}
    monthly = rates.get("LTV1", 0.0) / year_one
    uprate, upamt = m.upgrade_rates(band)
    running = 0.0
    for mth in range(1, C.HORIZON_MONTHS + 1):
        running += monthly * curve[mth]
        if mth > 12:
            running += uprate * upamt * curve[mth]
        if running >= fee:
            return mth, gross / fee
    return None, gross / fee


PAYBACK_BANDS = ["€10", "€12–13", "€15", "€20"]


def payback(m: Model, bands) -> str:
    rows = []
    for band in PAYBACK_BANDS:
        if band not in bands.index:
            continue
        fee = float(bands.loc[band, "blended_cpa"])
        mth, roi = _payback_months(m, band, fee)
        rows.append((band, mth, roi))
    return G.payback(rows)


# ----------------------------------------------------------- 9 · fee cap ----
def fee_cap(m: Model, bands) -> str:
    """
    What the cap costs an agency to honour - which is nothing.

    Above the cap the fee stops rising while the donor's value keeps climbing,
    so every step up is income to us at no extra cost. The chart prices each
    step for the two agencies the cap applies to.
    """
    states = []
    for agency in [a for a in m.cost_table.index if a in C.FEE_CAP]:
        cap = C.FEE_CAP[agency]
        factor = float(m.cost_table.loc[agency, "cpa_factor"])
        base_band = "€%d" % int(cap)
        base_gross = m.gross_ltv_profile(base_band, m.age_profile(agency))
        if base_gross is None:
            continue
        # Above the top band we have donors for, value scales with the gift:
        # the retention curve is the band's, the gift is what changes.
        top = C.BAND_ORDER[-2] if C.BAND_ORDER[-1] == "Other" else C.BAND_ORDER[-1]
        top_gift = C.BAND_GIFT.get(top, cap)
        top_gross = m.gross_ltv_profile(top, m.age_profile(agency)) or base_gross
        rows = []
        for gift in CAP_STEPS:
            band = "€%d" % gift
            gross = m.gross_ltv_profile(band, m.age_profile(agency)) \
                if band in m.band_rates else None
            if gross is None:
                gross = top_gross / top_gift * gift
            rows.append((gift, gross - base_gross, factor * gift - factor * cap))
        states.append((
            agency,
            "%s - what each step above the €%d cap is worth" % (agency, int(cap)),
            G.cap_steps(rows, cap),
            "Each step above €%d for one donor, on %s&rsquo;s own age profile and "
            "own fee rate. The fee under the cap does not move; the grey bar is "
            "what it would be without the cap." % (int(cap), agency),
        ))
    return G.sliced("cap", states)


# -------------------------------------------------- 10 · donors we'd need ---
def _levels(m: Model, agency: str) -> tuple:
    """An agency's main ask, and the amounts it acquires at in any number."""
    shares = m.band_share(agency)
    levels = [b for b in C.BAND_ORDER
              if b != "Other" and shares.get(b, 0.0) >= C.MIN_SHARE
              and m.agency_net(agency, b) is not None]
    if not levels:
        return None, [], shares
    # The main ask is the amount they sell most of - but where two amounts are
    # within a couple of points of each other the mode flips on noise, so the
    # lower of them is taken. That is the ask a rollback would be measured
    # against, and it is the conservative choice: it makes the higher amounts
    # prove more, not less.
    top = max(shares.get(b, 0.0) for b in levels)
    base = next(b for b in levels if shares.get(b, 0.0) >= top - C.MAIN_ASK_TOL)
    return base, levels, shares


def headroom(m: Model, bands) -> str:
    states = []
    for agency in m.cost_table.index:
        base, levels, shares = _levels(m, agency)
        if base is None:
            continue
        base_net = m.agency_net(agency, base)
        if not base_net or base_net <= 0:
            continue
        base_income = 1000 * base_net
        need = {}
        for level in levels:
            net = m.agency_net(agency, level)
            need[level] = base_income / net if net and net > 0 else float("nan")
        levels = [l for l in levels if np.isfinite(need[l])]
        if not levels:
            continue
        states.append((
            agency,
            "Donors needed to match the %s that 1,000 donors at %s deliver"
            % (G.money(base_income), base),
            G.headroom(levels, need, shares, base, base_income),
            "Price points where %s acquires fewer than %g%% of its donors are "
            "hidden. Each agency is valued on its own age profile and charged "
            "its own fee." % (agency, C.MIN_SHARE),
        ))
    return G.sliced("hf", states)


# -------------------------------------------- 11 · retention in reserve -----
def _profile_curve(m: Model, band: str, profile: dict):
    """A band's survival curve weighted across one agency's age profile."""
    total, weight = None, 0.0
    for ab, w in profile.items():
        if w <= 0:
            continue
        c = m.curve(band, ab)
        if c is None:
            continue
        total = w * c if total is None else total + w * c
        weight += w
    return total / weight if weight > 0 else None


def _breakeven_retention(m: Model, agency: str, band: str,
                         target_net: float) -> float | None:
    """
    The 12-month retention at which a band stops beating the main ask.

    Everything here is measured on the agency's own donors - their age profile
    and their fee - because that is what it is being compared against. Valuing
    the higher amount on the market as a whole while comparing it to this
    agency's main ask would mix two different populations and understate the
    margin.

    The curve is scaled through its cumulative hazard, which keeps the shape of
    the decay and pivots it on the twelve-month figure - the same adjustment
    the scenario planner makes when someone moves the retention lever.
    """
    profile = m.age_profile(agency)
    curve = _profile_curve(m, band, profile)
    gross = m.gross_ltv_profile(band, profile)
    fee = m.cpa(agency, band)
    if curve is None or gross is None or not np.isfinite(fee):
        return None
    base = S.annuity(curve, 1, C.HORIZON_MONTHS)
    if base <= 0:
        return None
    r12 = float(curve[12])
    lo, hi = 0.02, min(r12, 0.999)
    for _ in range(60):
        mid = (lo + hi) / 2
        k = np.log(mid) / np.log(r12) if 0 < r12 < 1 else 1.0
        scaled = np.where(curve > 0, np.exp(k * np.log(np.maximum(curve, 1e-9))), 0.0)
        scaled[0] = 1.0
        net = gross * S.annuity(scaled, 1, C.HORIZON_MONTHS) / base - fee
        if net > target_net:
            hi = mid
        else:
            lo = mid
    return 100 * (lo + hi) / 2


def reserve(m: Model, bands) -> str:
    states = []
    for agency in m.cost_table.index:
        base, levels, shares = _levels(m, agency)
        if base is None:
            continue
        base_net = m.agency_net(agency, base)
        base_gift = C.BAND_GIFT.get(base, 0.0)
        rows = []
        profile = m.age_profile(agency)
        for level in levels:
            if C.BAND_GIFT.get(level, 0.0) <= base_gift:
                continue
            curve = _profile_curve(m, level, profile)
            if curve is None:
                continue
            be = _breakeven_retention(m, agency, level, base_net)
            if be is None:
                continue
            rows.append((level, base, 100 * float(curve[12]), be))
        if not rows:
            continue
        states.append((
            agency,
            "Retention in reserve at %s - main ask %s" % (agency, base),
            G.reserve(rows),
            "How far twelve-month retention on the higher amount could fall "
            "before it stopped beating that agency&rsquo;s main ask on ten-year "
            "net value.",
        ))
    return G.sliced("rb", states)


# ------------------------------------------------------------------ all -----
BUILDERS = {
    1: volumes,
    2: behaviour,
    3: gross_ltv,
    4: by_age,
    5: retention,
    6: agencies,
    7: net_ltv,
    8: fee_cap,
    9: headroom,
    10: reserve,
}


def build(m: Model, bands, captioned=()) -> dict:
    """
    Every figure the report can draw, keyed by its number.

    `captioned` lists the figures the narrative already writes a caption for.
    Those keep the written caption and drop the generated one, so no figure
    ends up explained twice.
    """
    out = {}
    for number, fn in BUILDERS.items():
        try:
            html = fn(m, bands)
        except Exception as exc:                      # pragma: no cover
            print("  figure %d could not be built: %s" % (number, exc))
            continue
        if number in captioned:
            html = re.sub(r"<figcaption>.*?</figcaption>", "", html, flags=re.S)
        out[number] = html
    return out
