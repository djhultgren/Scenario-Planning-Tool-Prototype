"""
Retention curves and their projection beyond the observed window.

Two ideas do the work here.

1. Between the observed anchor points we interpolate on *cumulative hazard*
   rather than in a straight line. Retention decays geometrically - a roughly
   constant proportion of the survivors leaves each month, not a constant
   number - so linear interpolation between, say, month 12 and month 24 would
   systematically overstate the months in between.

2. Beyond month 60 there is nothing to observe, so we project with a shifted
   beta-geometric model (Fader & Hardie). It assumes donors are not identical:
   each has their own lapse probability, drawn from a beta distribution. The
   least committed leave early, so the survivors are progressively more loyal
   and the retention rate improves on its own. That is why the projected years
   flatten instead of continuing to fall at the year-one rate.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln

from . import config as C


# ------------------------------------------------------- interpolation -----
def curve_from_anchors(anchors: list[tuple[int, float]], horizon: int) -> np.ndarray:
    """
    Build a monthly survival curve from (month, survival) anchor points.

    `anchors` must start at (0, 1.0) and be in ascending month order with
    survival in 0..1. Returns an array of length horizon+1 where element t is
    the share of the cohort still giving at month t.
    """
    months = [m for m, _ in anchors]
    vals = [max(min(float(s), 1.0), 1e-9) for _, s in anchors]
    H = np.zeros(len(vals))                       # cumulative hazard
    H[:] = [-np.log(v) for v in vals]

    out = np.ones(horizon + 1)
    for t in range(1, horizon + 1):
        if t <= months[-1]:
            j = np.searchsorted(months, t)
            m0, m1 = months[j - 1], months[j]
            h0, h1 = H[j - 1], H[j]
            frac = (t - m0) / (m1 - m0)
            out[t] = np.exp(-(h0 + frac * (h1 - h0)))
        else:                                      # flat beyond the last anchor
            out[t] = out[months[-1]]
    return np.clip(out, 1e-9, 1.0)


# ---------------------------------------------------------------- sBG -----
def sbg_survival(alpha: float, beta: float, periods: int) -> list[float]:
    """Shifted beta-geometric survival at the end of each period."""
    return [float(np.exp(betaln(alpha, beta + t) - betaln(alpha, beta)))
            for t in range(1, periods + 1)]


def fit_sbg(observed: list[float]) -> tuple[float, float]:
    """
    Fit alpha and beta to a sequence of annual survival values.

    `observed[i]` is the share still giving at the end of year i+1. Fitted by
    least squares on the survival values, in log-parameter space to keep both
    parameters positive.
    """
    obs = np.asarray(observed, dtype=float)

    def loss(theta):
        a, b = np.exp(theta)
        pred = np.asarray(sbg_survival(a, b, len(obs)))
        return float(np.sum((pred - obs) ** 2))

    res = minimize(loss, np.asarray(C.SBG_INIT), method="Nelder-Mead",
                   options={"maxiter": C.SBG_MAXITER, "xatol": 1e-8, "fatol": 1e-12})
    return tuple(np.exp(res.x))


def project_annual(observed: list[float], to_year: int) -> list[float]:
    """
    Extend a sequence of annual survival values out to `to_year`.

    Returns the full sequence, observed years first then projected.
    """
    alpha, beta = fit_sbg(observed)
    full = sbg_survival(alpha, beta, to_year)
    # Anchor the projection to the last observed point so the two join cleanly.
    scale = observed[-1] / full[len(observed) - 1]
    return list(observed) + [v * scale for v in full[len(observed):]]


# --------------------------------------------------------- aggregation -----
def annuity(curve: np.ndarray, first_month: int, last_month: int) -> float:
    """Sum of survival over a month range - the expected months of giving."""
    return float(np.sum(curve[first_month:last_month + 1]))
