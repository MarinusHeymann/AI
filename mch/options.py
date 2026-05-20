"""Black-Scholes pricing and implied-vol proxy helpers.

No live options data is available; we price all option legs with BS using a
realized-vol * premium proxy for implied vol (config.IV_PREMIUM_MULT).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import config as C


# --------------------------------------------------------------------------
# Realized volatility (rolling 30-day, annualised)
# --------------------------------------------------------------------------
def realized_vol(prices: pd.DataFrame, window: int = C.RV_WINDOW) -> pd.DataFrame:
    log_ret = np.log(prices).diff()
    return log_ret.rolling(window).std() * np.sqrt(252)


def iv_from_rv(rv: float, mult: float = C.IV_PREMIUM_MULT) -> float:
    if np.isnan(rv) or rv <= 0:
        return 0.25
    return max(0.08, rv * mult)


# --------------------------------------------------------------------------
# Black-Scholes (European, no dividends)
# --------------------------------------------------------------------------
def _d1(S: float, K: float, T: float, r: float, sig: float) -> float:
    return (np.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))


def bs_call_price(S: float, K: float, T: float, r: float, sig: float) -> float:
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    d1 = _d1(S, K, T, r, sig)
    d2 = d1 - sig * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_call_delta(S: float, K: float, T: float, r: float, sig: float) -> float:
    if T <= 0:
        return 1.0 if S > K else 0.0
    if sig <= 0:
        return 1.0 if S > K else 0.0
    return float(norm.cdf(_d1(S, K, T, r, sig)))


def strike_for_delta(
    S: float, T: float, r: float, sig: float, target_delta: float
) -> float:
    """Find strike such that call delta == target_delta.

    Analytical inversion of the BS delta formula.
    """
    if T <= 0 or sig <= 0:
        return S
    inv = norm.ppf(target_delta)
    # d1 = inv => ln(S/K) = inv*sig*sqrt(T) - (r + 0.5*sig^2)*T
    ln_ratio = inv * sig * np.sqrt(T) - (r + 0.5 * sig * sig) * T
    return float(S / np.exp(ln_ratio))
