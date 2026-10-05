"""
Configuration for the Germany F2F lifetime value model.

Everything that is a judgement call rather than a calculation lives here, so it
can be changed without touching the model code.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths -----
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"

HISTORIC_FILE = DATA / "historic_donors.xlsx"      # behaviour: retention, upgrades
COHORT_FILE = DATA / "cohort_2026.xlsx"            # who we are acquiring now
COHORT_SHEET = "data"
COSTS_FILE = DATA / "agency_costs.xlsx"            # agency fee schedule

# ------------------------------------------------------------- horizons -----
HORIZON_MONTHS = 120          # ten years
OBSERVED_MONTHS = 60          # months 1-60 come from donor records
RETENTION_ANCHORS = [3, 12, 24, 36, 48, 60]

# ---------------------------------------------------------- gift banding -----
# Upper bound (exclusive) for each band, in monthly-equivalent euros.
GIFT_BANDS = [
    ("€5", 6.5),
    ("€8", 9.0),
    ("€10", 11.5),
    ("€12–13", 14.0),
    ("€15", 17.5),
    ("€20", 22.5),
    ("€25", 27.5),
    ("€30", 32.5),
]
OTHER_BAND = "Other"
BAND_ORDER = [b for b, _ in GIFT_BANDS] + [OTHER_BAND]

# Representative monthly gift used when pricing a band (fees are charged on this).
BAND_GIFT = {
    "€5": 5.0, "€8": 8.0, "€10": 10.0, "€12–13": 12.5,
    "€15": 15.0, "€20": 20.0, "€25": 25.0, "€30": 30.0,
}

# ----------------------------------------------------------- age banding -----
# Age at sign-up, not age today. See README.
AGE_BANDS = [
    ("18–29", 0, 29.999),
    ("30–39", 30, 39.999),
    ("40–49", 40, 49.999),
    ("50–64", 50, 64.999),
    ("65+", 65, 200),
]
AGE_ORDER = [b for b, _, _ in AGE_BANDS]

# Ages outside this range are treated as data errors and dropped.
AGE_MIN, AGE_MAX = 16, 100

# --------------------------------------------------- scenario planner -----
# The planner works in wider ranges than the report's point bands, because a
# plan is built by moving blocks of donors rather than by setting exact asks.
PLANNER_BANDS = [
    ("\u20ac5-10", 0, 10),
    ("\u20ac10-20", 10, 20),
    ("\u20ac20-30", 20, 30),
    ("\u20ac30-50", 30, 50),
    ("\u20ac50-100", 50, 100),
]
PLANNER_HORIZONS = [1, 3, 5, 10]     # years offered in the horizon switch
DEFAULT_CAP = 20.0                   # euros per month

# The cost file covers the first half of the year. Volumes are annualised by
# this factor so the plan describes a full year of acquisition. Set to 1.0 if
# a full-year cost file is supplied.
ANNUALISE = 2.0

# ----------------------------------------------- non-monthly retention -----
# Monthly donors have observable retention: a missed payment shows up within a
# month. Non-monthly donors do not. An annual donor cannot lapse before their
# second gift falls due at month 12, so the retention flags record them as
# fully retained for a year whatever they go on to do, and the first
# meaningful checkpoint is month 24.
#
# Rather than read that artefact as loyalty, annual and quarterly donors use
# the observed retention schedules below: share of the cohort still giving at
# the end of each year. Monthly and twice-yearly donors keep their own
# observed curve.
FREQUENCY_RETENTION = {
    "A": [1.00, 0.80, 0.70, 0.60, 0.50],
    "Q": [0.68, 0.60, 0.55, 0.50, 0.45],
}

# -------------------------------------------------------------- filters -----
CHANNEL = "F2F"
AGENCY_FLAG = "AG"
BEHAVIOUR_YEARS = (2022, 2024)     # cohorts used for 12m/24m behaviour
MIN_CELL = 30                      # below this a cell falls back to the band average
MIN_TAIL_OBS = 50                  # minimum observations to trust a year 3-5 rate
LOW_BASE = 50                      # cells below this are flagged "low base" in outputs
# An agency's price point is only shown where it acquires at least this
# share of its donors - below it, the cell is too thin to price honestly.
MIN_SHARE = 1.0        # per cent of an agency's own donors
# Two price points this close in share are treated as the same main ask, and
# the lower one is used.
MAIN_ASK_TOL = 2.0     # percentage points

# ------------------------------------------------------------- agencies -----
# Maps the BINGO source code to an agency name. Codes not listed here are
# treated as unattributed and excluded from the behavioural base (they remain
# in the income totals, which are driven by the cost file).
SOURCE_CODE_MAP = {
    "F2F_TruMa_Unrestr": "Trust",
    "F2F_Apollon_Unrestr": "Apollon",
    "F2F_ACT_2_Unrestr": "Activate",
    "F2F_Wesser_Unrestr": "Wesser",
    "F2F_Direct_Result_Unrestr": "Direct Result",
}

# Agencies operating a fee cap, and the level it bites at.
FEE_CAP = {"Trust": 20.0, "Activate": 20.0}

# --------------------------------------------------------- sBG projection ----
SBG_INIT = (0.0, 0.0)              # log-alpha, log-beta starting point
SBG_MAXITER = 2000

# ------------------------------------------------------------------ theme ----
# Two looks, same numbers. "house" is the working style the report was drafted
# in; "sci" is the Save the Children International system - Oswald and Lato,
# red as the lead colour, the adult secondary palette for charts. Switch with
# `python run.py --theme sci`, or set THEME here to change the default.
THEME = "house"

THEMES = {
    "house": {
        # dark, red, accent, muted text, rules, panel fill
        "palette": ("#12324A", "#C8102E", "#2E7D5B",
                    "#5B6B78", "#E3E9EE", "#F4F7FA"),
        "bands": {
            "€5": "#8FC9A9", "€8": "#7FBFA0", "€10": "#5AA9CF",
            "€12–13": "#8AA0AE", "€15": "#B5822B", "€20": "#12324A",
            "€25": "#C58B3A", "€30": "#2C6E9B", "Other": "#B9C4CC",
        },
    },
    "sci": {
        # Black #222221, Red #DA291C (Pantone 485), Teal #009CA6,
        # Dark Grey #4A4F53, a biscuit rule, Biscuit 25% #F3F2EE.
        "palette": ("#222221", "#DA291C", "#009CA6",
                    "#4A4F53", "#E5E2DA", "#F3F2EE"),
        # Secondary palette, adult audience, at full strength - no tints and
        # no opacity changes, which the brand system does not permit.
        "bands": {
            "€5": "#D1CCBD",      # Biscuit
            "€8": "#F2A900",      # Mustard
            "€10": "#009CA6",     # Teal
            "€12–13": "#4A4F53",  # Dark Grey
            "€15": "#FC4C02",     # Orange
            "€20": "#DA291C",     # Red - the lead colour for the lead band
            "€25": "#9A3324",     # Plum
            "€30": "#222221",     # Black
            "Other": "#999999",   # Light Grey
        },
    },
}

NAVY, RED, GREEN, MUT, LINE, LIGHT = THEMES[THEME]["palette"]
BAND_COLOUR = dict(THEMES[THEME]["bands"])
TABLE_HEAD = "#009CA6"    # brand tables take a teal header; overridden below


def apply_theme(name: str):
    """Switch the look. Call before building charts or the report."""
    global THEME, NAVY, RED, GREEN, MUT, LINE, LIGHT, BAND_COLOUR, TABLE_HEAD
    if name not in THEMES:
        raise ValueError("unknown theme %r - choose from %s"
                         % (name, ", ".join(THEMES)))
    THEME = name
    NAVY, RED, GREEN, MUT, LINE, LIGHT = THEMES[name]["palette"]
    BAND_COLOUR = dict(THEMES[name]["bands"])
    TABLE_HEAD = "#009CA6" if name == "sci" else NAVY


apply_theme(THEME)
