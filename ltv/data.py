"""
Loading and preparing the three source files.

Two donor populations are used for two different purposes:

  historic()  - donors acquired 2019-2025. Tells us how donors *behave*:
                retention at months 3-60 and upgrade rates.
  cohort()    - donors acquired in the 2026 window. Tells us who we are
                *acquiring now*: volumes, gift amounts, ages and agency.

Both extracts supply age directly, as age at the point of acquisition. That
is the basis the model needs: the decision it informs is what to ask the
person in front of the fundraiser, and their age at that moment is the input.

They are deliberately kept apart. The model never takes behaviour from the
2026 cohort (too recent to have retention) and never takes volumes or age
profile from the historic file (the wrong population).
"""
import numpy as np
import pandas as pd

from . import config as C


# ------------------------------------------------------------- banding -----
def gift_band(monthly: float) -> str:
    """Monthly-equivalent gift -> band label."""
    if monthly is None or not np.isfinite(monthly):
        return C.OTHER_BAND
    for label, upper in C.GIFT_BANDS:
        if monthly < upper:
            return label
    return C.OTHER_BAND


def age_band(age: float) -> str | None:
    if age is None or not np.isfinite(age):
        return None
    for label, lo, hi in C.AGE_BANDS:
        if lo <= age <= hi:
            return label
    return None


def read_age(frame: pd.DataFrame, column: str = "Age") -> pd.Series:
    """
    Age at acquisition, read from the source file.

    Values outside AGE_MIN..AGE_MAX are data errors and become NaN, which
    drops the donor from the age-banded figures but leaves them in the totals.
    """
    age = pd.to_numeric(frame[column], errors="coerce")
    return age.where((age >= C.AGE_MIN) & (age <= C.AGE_MAX))


def monthly_equivalent(amount: float, frequency: str) -> float:
    """
    Convert a pledge to a monthly equivalent.

    The agency fee is charged on the monthly figure, and it is the only way to
    compare an annual donor with a monthly one. A EUR60-a-year donor is EUR5 a
    month in the model.
    """
    per_year = {"M": 12, "Q": 4, "SA": 2, "A": 1}.get(str(frequency).strip().upper())
    if per_year is None or amount is None or not np.isfinite(amount):
        return np.nan
    return amount * per_year / 12.0


# ------------------------------------------------------------ historic -----
def historic() -> pd.DataFrame:
    """
    Behaviour base: F2F agency-acquired donors with their retention flags.

    Returns one row per donor with `band`, `ab` (age band), `age`, retention
    columns and first-year value.
    """
    d = pd.read_excel(C.HISTORIC_FILE)
    d = d[(d["ReportingChannel"] == C.CHANNEL) &
          (d["Inhouse/Agency"] == C.AGENCY_FLAG)].copy()

    d["monthly"] = d["FirstGiftAmount_MonthlyEquiv"].astype(float)
    d["band"] = d["monthly"].apply(gift_band)

    d["age"] = read_age(d)
    d["ab"] = d["age"].apply(age_band)

    d["upgraded"] = d["UpgradedBy12m"].fillna(0).astype(float)
    d["uplift"] = (d["LatestGiftAmount_MonthlyEquiv"].astype(float)
                   - d["monthly"]).clip(lower=0)
    return d


# -------------------------------------------------------------- cohort -----
def cohort() -> pd.DataFrame:
    """
    The population we are acquiring now: one row per 2026 pledge.

    Adds `agency` (None where the source code is a venue rather than an
    agency), `band`, `age` and `ab`.
    """
    d = pd.read_excel(C.COHORT_FILE, sheet_name=C.COHORT_SHEET)
    d = d.rename(columns={
        "RegularGivingPledgeGiftAmount": "amount",
        "RegularGivingPledgeFrequency": "freq",
        "RegularGivingPledgeSourceCode": "source_code",
        "RegularGivingPledgeDate": "pledge_date",
    })
    d["monthly"] = [monthly_equivalent(a, f)
                    for a, f in zip(d["amount"], d["freq"])]
    d["band"] = d["monthly"].apply(gift_band)
    d["agency"] = d["source_code"].map(C.SOURCE_CODE_MAP)

    d["age"] = read_age(d)
    d["ab"] = d["age"].apply(age_band)
    return d


# --------------------------------------------------------------- costs -----
def costs() -> pd.DataFrame:
    """
    Agency fee schedule.

    Returns one row per agency with the CPA factor (multiple of the monthly
    gift), the cost-per-sign-up factor, realised donor and sign-up counts, and
    the fee cap where one applies.
    """
    raw = pd.read_excel(C.COSTS_FILE, header=0)
    raw = raw[raw["Partner"].notna() & (raw["Partner"] != "Total/Avg")].copy()

    def num(series):
        return pd.to_numeric(
            series.astype(str)
                  .str.replace("€", "", regex=False)
                  .str.replace("\xa0", "", regex=False)
                  .str.replace(".", "", regex=False)
                  .str.replace(",", ".", regex=False)
                  .str.strip(),
            errors="coerce")

    out = pd.DataFrame({
        "agency": raw["Partner"].astype(str).str.strip(),
        "cpa_factor": num(raw["Actual CPA factor"]),
        "cpsu_factor": num(raw["Actual CPSU factor"]),
        "sign_ups": pd.to_numeric(raw["Sign-Ups"], errors="coerce"),
        "realised_donors": pd.to_numeric(raw["Realized Donors"], errors="coerce"),
        "total_cost": pd.to_numeric(raw["Cost EUR"], errors="coerce"),
    })
    out["cap"] = out["agency"].map(C.FEE_CAP)
    return out.set_index("agency")


def cpa(agency: str, band: str, cost_table: pd.DataFrame,
        apply_cap: bool = True, gift: float | None = None) -> float:
    """
    What we pay to acquire one donor at this gift band from this agency.

    The fee is the agency's own factor times the monthly gift. Where a cap is
    in force the gift is capped first, so a EUR30 donor costs the same as a
    EUR20 one.
    """
    gift = C.BAND_GIFT.get(band) if gift is None else gift
    if gift is None or not np.isfinite(gift) or agency not in cost_table.index:
        return np.nan
    row = cost_table.loc[agency]
    if apply_cap and np.isfinite(row.get("cap", np.nan)):
        gift = min(gift, float(row["cap"]))
    return float(row["cpa_factor"]) * gift
