"""Synthetic regime-aware price path generator.

Design
------
Per-ticker daily log return is decomposed as::

    ret_t = mu_target/252  +  beta * (mkt_shock_t - mkt_mu_t)  +  idio_shock_t

where ``mu_target`` is the calibrated long-run annual drift for the ticker. By
centring the beta exposure on the market's instantaneous drift, the per-ticker
expected drift equals ``mu_target`` regardless of beta. Regime windows
override ``mkt_mu_t`` and ``mkt_sig_t`` to inject crisis drawdowns and vol
spikes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def _business_days(start: str, end: str) -> pd.DatetimeIndex:
    return pd.bdate_range(start, end)


def _regime_overlays(dates: pd.DatetimeIndex):
    n = len(dates)
    d = np.zeros(n)
    v = np.zeros(n)
    vf = np.zeros(n)
    for start, end, dd, dv, f in C.REGIMES:
        mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
        d[mask] += dd
        v[mask] += dv
        vf[mask] = np.maximum(vf[mask], f)
    return d, v, vf


def generate_prices() -> pd.DataFrame:
    rng = np.random.default_rng(C.SEED)
    dates = _business_days(C.START, C.END)
    n = len(dates)

    # --------------------------------------------------------------------
    # Market factor (SPY). Base drift is chosen so that AFTER regime drag
    # the 30-year CAGR lands near ~9%. Regime-drift windows are modest in
    # daily magnitude but integrate to the correct peak-to-trough drawdown.
    # --------------------------------------------------------------------
    base_mkt_mu_a = 0.125          # base 12.5% annual, regimes will drag it
    base_mkt_sig_a = 0.15
    base_mkt_mu = base_mkt_mu_a / 252
    base_mkt_sig = base_mkt_sig_a / np.sqrt(252)

    extra_d, extra_v, vix_floor = _regime_overlays(dates)
    mkt_mu_t = base_mkt_mu + extra_d
    mkt_sig_t = base_mkt_sig + extra_v

    mkt_eps = rng.standard_normal(n)
    mkt_ret = mkt_mu_t + mkt_sig_t * mkt_eps             # log returns
    mkt_shock = mkt_ret - mkt_mu_t                        # centred shocks

    spy = 100.0 * np.exp(np.cumsum(mkt_ret))
    out: dict[str, pd.Series] = {"SPY": pd.Series(spy, index=dates)}

    # --------------------------------------------------------------------
    # Per-ticker path. Idio vol is backed out so total vol ~= target_vol_a
    # when combined with beta * base_mkt_sig.
    # --------------------------------------------------------------------
    for tkr, (drift_a, vol_a, beta) in C.TICKER_PARAMS.items():
        sys_var_a = (beta * base_mkt_sig_a) ** 2
        idio_var_a = max(vol_a * vol_a - sys_var_a, (0.05) ** 2)
        idio_sig = np.sqrt(idio_var_a) / np.sqrt(252)
        idio_eps = rng.standard_normal(n)
        ret = drift_a / 252 + beta * mkt_shock + idio_sig * idio_eps
        out[tkr] = pd.Series(100.0 * np.exp(np.cumsum(ret)), index=dates)

    # --------------------------------------------------------------------
    # QQQ proxy: equal-weight tech basket.
    # --------------------------------------------------------------------
    tech = ["AAPL", "NVDA", "META", "GOOGL", "AMZN", "MSFT", "NOW", "PANW"]
    qqq_levels = sum(out[t] for t in tech) / len(tech)
    out["QQQ"] = qqq_levels / qqq_levels.iloc[0] * 100.0

    # --------------------------------------------------------------------
    # TLT proxy: bond, modestly negatively correlated to market shocks.
    # --------------------------------------------------------------------
    bond_mu = 0.045 / 252
    bond_sig = 0.11 / np.sqrt(252)
    bond_eps = rng.standard_normal(n)
    tlt_ret = bond_mu + bond_sig * bond_eps - 0.25 * mkt_shock
    out["TLT"] = pd.Series(100.0 * np.exp(np.cumsum(tlt_ret)), index=dates)

    # --------------------------------------------------------------------
    # VIX proxy: log-OU, mean-reverting with regime floor lifts.
    # --------------------------------------------------------------------
    vix = np.zeros(n)
    vix[0] = 18.0
    kappa = 0.10
    vov = 0.14
    for i in range(1, n):
        longrun = max(18.0, vix_floor[i])
        # VIX spikes on down market days.
        mkt_effect = -mkt_eps[i] * 0.06
        shock = rng.normal(0, vov)
        ln_next = (
            np.log(vix[i - 1])
            + kappa * (np.log(longrun) - np.log(vix[i - 1]))
            + mkt_effect
            + shock
        )
        vix[i] = float(max(9.0, min(95.0, np.exp(ln_next))))
    out["^VIX"] = pd.Series(vix, index=dates)

    df = pd.DataFrame(out)
    df.index.name = "date"
    return df


def synth_earnings_calendar(dates: pd.DatetimeIndex) -> dict[str, set[pd.Timestamp]]:
    """Four synthetic prints per name per year, roughly late-Jan/Apr/Jul/Oct."""
    months_of_year = [1, 4, 7, 10]
    days = [28, 25, 29, 27]
    cal: dict[str, set[pd.Timestamp]] = {}
    years = sorted({d.year for d in dates})
    for i, tkr in enumerate(C.TICKERS):
        s: set[pd.Timestamp] = set()
        for y in years:
            for m, d in zip(months_of_year, days):
                d_adj = min(28, max(1, d + (i % 5) - 2))
                ts = pd.Timestamp(y, m, d_adj)
                while ts.weekday() >= 5:
                    ts -= pd.Timedelta(days=1)
                if dates[0] <= ts <= dates[-1]:
                    s.add(ts)
        cal[tkr] = s
    return cal
