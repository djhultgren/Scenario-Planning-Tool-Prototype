"""
The lifetime value model.

Sequence:

  1. Observe retention for each gift band x age band from the historic donors.
  2. Extend each age band's curve to ten years with the sBG projection.
  3. Convert survival into income: effective monthly gift x months of giving,
     plus the upgrade uplift from month 13.
  4. Subtract the acquisition fee - each donor at their own agency's rate,
     capped where a cap applies.

Every figure the report and the scenario tool use comes out of `Model`.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config as C
from . import data as D
from . import survival as S


def _safe(x, default: float = 0.0) -> float:
    """NaN is truthy in Python, so `x or 0.0` does not do what it looks like."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if np.isfinite(v) else default


@dataclass
class Model:
    historic: pd.DataFrame
    cohort: pd.DataFrame
    cost_table: pd.DataFrame
    cells: dict = field(default_factory=dict)       # (band, age band) -> rates
    band_rates: dict = field(default_factory=dict)  # band -> pooled rates
    tail: dict = field(default_factory=dict)        # age band -> annual rates
    _curves: dict = field(default_factory=dict)

    # ------------------------------------------------------------ build -----
    @classmethod
    def build(cls) -> "Model":
        m = cls(historic=D.historic(), cohort=D.cohort(), cost_table=D.costs())
        m._measure_behaviour()
        m._measure_tail()
        return m

    def _behaviour_frame(self) -> pd.DataFrame:
        lo, hi = C.BEHAVIOUR_YEARS
        h = self.historic
        return h[h["AcquisitionYear"].between(lo, hi)]

    @staticmethod
    def _rates(sub: pd.DataFrame) -> dict | None:
        """Observed retention and first-year value for a group of donors."""
        if len(sub) < C.MIN_CELL:
            return None
        r12 = sub["RetainedMonth12"].mean()
        if not np.isfinite(r12):
            return None
        r3 = sub["RetainedMonth3"].mean()
        r24_obs = sub["RetainedMonth24"].dropna()
        r24 = r24_obs.mean() if len(r24_obs) >= C.MIN_CELL else r12 * 0.78
        ltv1 = sub["LTV_1yr_Local"].mean()
        if not np.isfinite(ltv1) or ltv1 <= 0:
            return None
        return {
            "n": int(len(sub)),
            "R3": float(max(r3, r12 * 1.001)),
            "R12": float(r12),
            "R24": float(min(r24, r12 * 0.999)),
            "LTV1": float(ltv1),
            "upgrade_rate": float(sub["upgraded"].mean()),
            "upgrade_amt": _safe(sub.loc[sub["upgraded"] > 0, "uplift"].mean()),
        }

    def _measure_behaviour(self):
        b = self._behaviour_frame()
        for band in C.BAND_ORDER:
            sb = b[b["band"] == band]
            pooled = self._rates(sb)
            if pooled:
                self.band_rates[band] = pooled
            for ab in C.AGE_ORDER:
                cell = self._rates(sb[sb["ab"] == ab])
                if cell:
                    self.cells[(band, ab)] = cell

    def _measure_tail(self):
        """
        Years 3, 4 and 5 conditional retention, measured per age band.

        Uses every acquisition year, not just the behaviour window: a donor
        acquired in 2023 cannot yet have a 48-month observation, so the older
        cohorts are the only place these rates exist. Getting this wrong -
        applying one pooled rate to every age band - was a real defect in an
        earlier version of this model.
        """
        h = self.historic
        for ab in C.AGE_ORDER:
            sub = h[h["ab"] == ab]
            rates, prev_col = {}, "RetainedMonth24"
            for year, col in ((3, "RetainedMonth36"), (4, "RetainedMonth48"),
                              (5, "RetainedMonth60")):
                s = sub[sub[col].notna()]
                if len(s) >= C.MIN_TAIL_OBS and s[prev_col].mean() > 0:
                    rates[year] = float(min(s[col].mean() / s[prev_col].mean(), 0.999))
                else:
                    rates[year] = rates.get(year - 1, 0.92)
                prev_col = col
            self.tail[ab] = rates

    # ----------------------------------------------------------- curves -----
    def frequency_mix(self, band: str) -> dict[str, float]:
        """
        Share of a band's 2026 donors on each payment frequency.

        Needed because retention means different things by frequency: see
        `schedule_curve`.
        """
        sub = self.cohort[self.cohort["band"] == band]
        if len(sub) == 0:
            return {"M": 1.0}
        counts = sub["freq"].astype(str).str.upper().value_counts(normalize=True)
        return {k: float(v) for k, v in counts.items()}

    def schedule_curve(self, code: str) -> np.ndarray | None:
        """
        Survival curve for a fixed retention schedule, by payment frequency.

        A donor paying annually cannot lapse before their second gift falls
        due, so their retention flags read as fully retained for a year
        whatever they go on to do. Reading that as loyalty would flatter every
        band with annual donors in it - which is most of the EUR5 band. These
        donors use the observed schedules in config instead.
        """
        schedule = C.FREQUENCY_RETENTION.get(code)
        if schedule is None:
            return None
        if code in self._curves:
            return self._curves[code]
        projected = S.project_annual(list(schedule), C.HORIZON_MONTHS // 12)
        anchors = [(0, 1.0)]
        for i, v in enumerate(projected, start=1):
            anchors.append((12 * i, v))
        curve = S.curve_from_anchors(anchors, C.HORIZON_MONTHS)
        self._curves[code] = curve
        return curve

    def observed_curve(self, band: str, ab: str) -> np.ndarray | None:
        """Survival built from this cell's own observed retention."""
        rates = self.cells.get((band, ab)) or self.band_rates.get(band)
        if rates is None:
            return None
        t = self.tail[ab]
        m36 = rates["R24"] * t[3]
        m48 = m36 * t[4]
        m60 = m48 * t[5]
        annual = [rates["R12"], rates["R24"], m36, m48, m60]
        projected = S.project_annual(annual, C.HORIZON_MONTHS // 12)
        anchors = [(0, 1.0), (3, rates["R3"])]
        for i, v in enumerate(projected, start=1):
            anchors.append((12 * i, v))
        return S.curve_from_anchors(anchors, C.HORIZON_MONTHS)

    def curve(self, band: str, ab: str) -> np.ndarray | None:
        """
        Ten-year monthly survival curve for one gift band x age band.

        A blend, weighted by how the band's donors actually pay: monthly and
        twice-yearly donors on their own observed retention, annual and
        quarterly donors on the fixed schedules in config.
        """
        key = (band, ab)
        if key in self._curves:
            return self._curves[key]
        observed = self.observed_curve(band, ab)
        if observed is None:
            return None

        total = np.zeros_like(observed)
        weight = 0.0
        for code, share in self.frequency_mix(band).items():
            if share <= 0:
                continue
            sched = self.schedule_curve(code)
            total += share * (sched if sched is not None else observed)
            weight += share
        curve = total / weight if weight > 0 else observed
        self._curves[key] = curve
        return curve

    # -------------------------------------------------------------- LTV -----
    def gross_ltv(self, band: str, ab: str, months: int = C.HORIZON_MONTHS) -> float | None:
        """
        Expected gross income from one donor over `months`.

        Effective monthly gift is implied by observed first-year value divided
        by the expected months of giving in year one - which nets off failed
        payments and part-years without having to model them separately.
        """
        rates = self.cells.get((band, ab)) or self.band_rates.get(band)
        curve = self.curve(band, ab)
        if rates is None or curve is None:
            return None
        year_one = S.annuity(curve, 1, 12)
        if year_one <= 0:
            return None
        monthly = rates["LTV1"] / year_one
        base = monthly * S.annuity(curve, 1, months)
        uplift = (rates["upgrade_rate"] * rates["upgrade_amt"]
                  * S.annuity(curve, 13, months))
        return float(base + uplift)

    def gross_ltv_profile(self, band: str, profile: dict[str, float],
                          months: int = C.HORIZON_MONTHS) -> float | None:
        """Gross LTV for a band, weighted across an age profile."""
        num = den = 0.0
        for ab, w in profile.items():
            if w <= 0:
                continue
            v = self.gross_ltv(band, ab, months)
            if v is None:
                continue
            num += w * v
            den += w
        return float(num / den) if den > 0 else None

    def band_gift(self, band: str) -> float:
        """
        The monthly gift a band is charged on.

        Standard bands use their representative amount. "Other" is a pooled
        catch-all, so its fee basis is the mean monthly gift of the donors who
        actually fall in it.
        """
        if band in C.BAND_GIFT:
            return C.BAND_GIFT[band]
        sub = self.cohort[self.cohort["band"] == band]["monthly"]
        return _safe(sub.mean(), 0.0)

    def cpa(self, agency: str, band: str, apply_cap: bool = True) -> float:
        return D.cpa(agency, band, self.cost_table, apply_cap,
                     gift=self.band_gift(band))

    # ------------------------------------------------------- age profiles ----
    def age_profile(self, agency: str | None = None,
                    band: str | None = None) -> dict[str, float]:
        """Share of donors in each age band, for the 2026 cohort."""
        c = self.cohort
        if agency:
            c = c[c["agency"] == agency]
        if band:
            c = c[c["band"] == band]
        c = c[c["ab"].notna()]
        if len(c) == 0:
            return {}
        counts = c["ab"].value_counts(normalize=True)
        return {ab: float(counts.get(ab, 0.0)) for ab in C.AGE_ORDER}

    # ------------------------------------------------------- figure inputs ---
    def cell_n(self, band: str, ab: str | None = None) -> int:
        """Historic donors behind a cell - what decides whether it is shown."""
        if ab is None or ab == "All":
            return int((self.band_rates.get(band) or {}).get("n", 0))
        return int((self.cells.get((band, ab)) or {}).get("n", 0))

    def gross_ltv_at(self, band: str, ab: str | None = None,
                     months: int = C.HORIZON_MONTHS) -> float | None:
        """Gross LTV for a band, either in one age band or across all of them."""
        if ab is None or ab == "All":
            return self.gross_ltv_profile(band, self.age_profile(band=band), months)
        if (band, ab) not in self.cells:
            return None
        return self.gross_ltv(band, ab, months)

    def blended_cpa(self, band: str) -> float:
        """What the four agencies charge at a band, weighted by their volumes."""
        vols = self.volumes()
        n = float(vols[band].sum()) if band in vols.columns else 0.0
        if n <= 0:
            return float("nan")
        return sum(float(vols.loc[a, band]) * self.cpa(a, band)
                   for a in vols.index if np.isfinite(self.cpa(a, band))) / n

    def curve_at(self, band: str, ab: str | None = None):
        """Survival curve for a band, in one age band or across all of them."""
        if ab is not None and ab != "All":
            return self.curve(band, ab) if (band, ab) in self.cells else None
        profile = self.age_profile(band=band)
        total, weight = None, 0.0
        for a, w in profile.items():
            if w <= 0:
                continue
            c = self.curve(band, a)
            if c is None:
                continue
            total = w * c if total is None else total + w * c
            weight += w
        return total / weight if weight > 0 else None

    def band_share(self, agency: str) -> dict[str, float]:
        """How an agency's donors split across the gift bands, as percentages."""
        sub = self.cohort[self.cohort["agency"] == agency]
        if len(sub) == 0:
            return {}
        counts = sub["band"].value_counts(normalize=True)
        return {b: float(counts.get(b, 0.0)) * 100 for b in C.BAND_ORDER}

    def agency_net(self, agency: str, band: str,
                   months: int = C.HORIZON_MONTHS) -> float | None:
        """
        Net LTV of a donor at one agency, at one gift amount.

        Valued on that agency's own age profile and charged its own fee, which
        is the only fair way to compare agencies: they approach different
        people and they charge different rates.
        """
        gross = self.gross_ltv_profile(band, self.age_profile(agency), months)
        fee = self.cpa(agency, band)
        if gross is None or not np.isfinite(fee):
            return None
        return gross - fee

    def upgrade_rates(self, band: str) -> tuple[float, float]:
        """Share of a band's donors who upgrade, and by how much a month."""
        rates = self.band_rates.get(band) or {}
        return (_safe(rates.get("upgrade_rate")), _safe(rates.get("upgrade_amt")))

    def mean_age(self, band: str) -> float:
        """Average age at acquisition, from the 2026 cohort."""
        sub = self.cohort[self.cohort["band"] == band]["age"]
        return _safe(sub.mean())

    # ------------------------------------------------------------ volumes ---
    def volumes(self) -> pd.DataFrame:
        """
        2026 donors per agency x gift band.

        The gift mix comes from the donor records; the totals are scaled to the
        realised-donor counts in the cost file, because the donor extract is
        incomplete and uneven between agencies, then annualised by
        config.ANNUALISE so the figures describe a full year.
        """
        c = self.cohort[self.cohort["agency"].notna()]
        mix = (c.groupby(["agency", "band"]).size()
                .unstack(fill_value=0)
                .reindex(columns=C.BAND_ORDER, fill_value=0))
        share = mix.div(mix.sum(axis=1), axis=0)
        realised = self.cost_table["realised_donors"].reindex(share.index)
        return share.mul(realised * C.ANNUALISE, axis=0)

    # ------------------------------------------------------------ economics -
    def agency_summary(self, apply_cap: bool = True,
                       months: int = C.HORIZON_MONTHS) -> pd.DataFrame:
        """Volumes, cost, gross and net income for each agency."""
        vols = self.volumes()
        rows = []
        for agency in vols.index:
            profile = self.age_profile(agency)
            donors = gross = cost = 0.0
            for band in C.BAND_ORDER:
                n = float(vols.loc[agency, band])
                if n <= 0:
                    continue
                ltv = self.gross_ltv_profile(band, profile, months)
                fee = self.cpa(agency, band, apply_cap)
                if ltv is None or not np.isfinite(fee):
                    continue
                donors += n
                gross += n * ltv
                cost += n * fee
            rows.append({
                "agency": agency,
                "donors": donors,
                "cpa_factor": float(self.cost_table.loc[agency, "cpa_factor"]),
                "capped": agency in C.FEE_CAP,
                "gross_income": gross,
                "cost": cost,
                "net_income": gross - cost,
                "net_ltv": (gross - cost) / donors if donors else np.nan,
                "avg_cpa": cost / donors if donors else np.nan,
            })
        return pd.DataFrame(rows).set_index("agency")

    def band_summary(self, months: int = C.HORIZON_MONTHS) -> pd.DataFrame:
        """
        The same economics cut by gift band rather than agency.

        Each band is valued on the age profile it actually acquires, and
        carries a blended CPA - the volume-weighted average of what the
        agencies charge at that band. Use this to compare gift amounts, never
        to price an individual agency.
        """
        vols = self.volumes()
        rows = []
        for band in C.BAND_ORDER:
            n = float(vols[band].sum())
            if n <= 0:
                continue
            ltv = self.gross_ltv_profile(band, self.age_profile(band=band), months)
            if ltv is None:
                continue
            fee = sum(float(vols.loc[a, band]) * self.cpa(a, band)
                      for a in vols.index
                      if np.isfinite(self.cpa(a, band))) / n
            rows.append({
                "band": band, "donors": n, "gross_ltv": ltv, "blended_cpa": fee,
                "net_ltv": ltv - fee, "gross_income": n * ltv,
                "net_income": n * (ltv - fee),
                "historic_n": (self.band_rates.get(band) or {}).get("n", 0),
            })
        return pd.DataFrame(rows).set_index("band")
