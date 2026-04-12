"""Portfolio, strategy, and simulation configuration for MCH backtest.

Notes
-----
Because this sandbox has no network access to financial data providers, the
backtest uses *synthetic* price paths calibrated to plausible drift/vol/
correlation/regime behaviour. The engine itself is real; the market data is
illustrative. Every assumption is centralized in this file so it is easy to
audit and sensitize.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------
START = "1996-04-01"
END = "2026-04-01"
SEED = 101

# --------------------------------------------------------------------------
# Capital
# --------------------------------------------------------------------------
INIT_CAPITAL = 800_000.0
SHARES_ALLOC = 400_000.0   # $400K deployed to common shares
LEAPS_ALLOC = 400_000.0    # $400K deployed to LEAPS premium
RISK_FREE = 0.03           # flat 3% for BS pricing; good enough for synth

# --------------------------------------------------------------------------
# Universe and tiers
# --------------------------------------------------------------------------
TICKERS = [
    "AAPL", "NVDA", "META", "MU", "GOOGL", "AMZN",
    "MSFT", "NOW", "HOOD", "BRK.B", "PANW", "GLD",
]

# Tier 1/2 names: covered calls written against share position.
TIER_CC = ["HOOD", "MU", "NOW", "NVDA", "PANW", "GOOGL", "AMZN"]

# Tier 3 names: PMCC — deep ITM LEAPS long leg, short OTM monthly call.
TIER_PMCC = ["AAPL", "META", "MSFT"]

# Untouched names: shares only, no overlay, no LEAPS.
NO_OVERLAY = ["BRK.B", "GLD"]

# Names that carry a LEAPS leg at all. BRK.B and GLD are shares-only.
LEAPS_UNIVERSE = [t for t in TICKERS if t not in NO_OVERLAY]

# Max single-name concentration (by total delta-equivalent exposure). 10% cap
# is honoured by construction (equal weight 12 names => 8.33% shares) but we
# re-check after LEAPS layering.
MAX_NAME_CONCENTRATION = 0.10

# --------------------------------------------------------------------------
# Per-ticker synthetic-data parameters (annual drift, annual vol, market beta)
# --------------------------------------------------------------------------
# Drift and vol reflect rough long-run history of each name over roughly the
# period it has existed (recent IPOs use an elevated drift to match post-IPO
# behaviour, then decay toward index). Betas come from published long-run
# regressions rounded for readability.
TICKER_PARAMS = {
    # ticker: (drift_annual, vol_annual, beta_to_market)
    # Drifts are *target total* annual log-drifts (pre-regime). The generator
    # centres the beta exposure so per-ticker drift equals this value
    # regardless of beta. Calibrated against rough long-run realised returns,
    # damped for the high-beta tech names so 30-year compounding is plausible.
    "AAPL":  (0.14, 0.30, 1.15),
    "NVDA":  (0.16, 0.45, 1.45),
    "META":  (0.12, 0.34, 1.25),
    "MU":    (0.07, 0.42, 1.55),
    "GOOGL": (0.13, 0.27, 1.10),
    "AMZN":  (0.15, 0.33, 1.25),
    "MSFT":  (0.13, 0.25, 1.05),
    "NOW":   (0.14, 0.35, 1.30),
    "HOOD":  (0.08, 0.55, 1.65),
    "BRK.B": (0.09, 0.17, 0.85),
    "PANW":  (0.14, 0.38, 1.25),
    "GLD":   (0.04, 0.15, -0.05),
}

# --------------------------------------------------------------------------
# Market regime shocks (crisis overlays)
# --------------------------------------------------------------------------
# Tuple: (start, end, extra_daily_market_drift, extra_daily_market_vol, vix_floor)
REGIMES = [
    ("2000-03-01", "2002-10-09", -0.00075, 0.010, 25.0),  # Dotcom bust
    ("2008-09-01", "2009-03-09", -0.00140, 0.018, 32.0),  # GFC
    ("2011-08-01", "2011-10-15", -0.00060, 0.010, 28.0),  # EU debt / US downgrade
    ("2015-08-15", "2015-10-01", -0.00050, 0.008, 22.0),  # China devaluation
    ("2018-12-01", "2018-12-31", -0.00070, 0.008, 22.0),  # Dec 2018
    ("2020-02-20", "2020-04-07", -0.00180, 0.028, 40.0),  # COVID
    ("2022-01-03", "2022-10-13", -0.00060, 0.008, 23.0),  # 2022 bear
]

# --------------------------------------------------------------------------
# Options overlay parameters
# --------------------------------------------------------------------------
LEAPS_DELTA_TARGET = 0.72
LEAPS_DTE_ENTRY = 450           # enter ~15-month LEAPS
LEAPS_DTE_ROLL = 240            # roll when 8 months remain
SHORT_CALL_DELTA_TARGET = 0.30
SHORT_CALL_DTE_ENTRY = 35       # open ~5-week call
SHORT_CALL_DTE_CLOSE = 7        # close at ~1 week unless earnings blackout
EARNINGS_BLACKOUT_DAYS = 5       # close 5 days pre-earnings (synthetic 4x/year)

# IV proxy: realized-vol (30d) * premium multiplier
IV_PREMIUM_MULT = 1.12
RV_WINDOW = 30

# --------------------------------------------------------------------------
# Risk management
# --------------------------------------------------------------------------
POSITION_STOP_LOSS = 0.25        # 25% drawdown from cost basis closes the name
POSITION_STOP_COOLDOWN = 10      # business days before allowed re-entry
CIRCUIT_BREAKER_DD = 0.22        # portfolio DD trigger
CIRCUIT_BREAKER_RECOVER = 0.05   # resume full risk when DD recovers to this
CORRELATION_BREAKER = 0.85       # rolling avg pairwise correl threshold
CORRELATION_WINDOW = 20

# --------------------------------------------------------------------------
# VIX tail hedge
# --------------------------------------------------------------------------
VIX_HEDGE_BUDGET_ANNUAL = 0.015  # spend ~1.5% of NAV / year on tail calls
VIX_HEDGE_STRIKE_OFFSET = 10.0   # strike = spot VIX + 10
VIX_HEDGE_DTE = 30
VIX_HEDGE_NOTIONAL_MULT = 100.0  # $ per VIX point

# --------------------------------------------------------------------------
# Benchmarks
# --------------------------------------------------------------------------
BENCHMARKS = ["SPY", "QQQ", "60_40"]

# --------------------------------------------------------------------------
# File paths (kept at repo root so resume is trivial)
# --------------------------------------------------------------------------
DATA_CACHE_FILE = "data_cache.pkl"
INTERIM_FILE = "backtest_interim_results.md"
REPORT_FILE = "MCH_Backtest_Report.md"
CHART_DIR = "charts"
