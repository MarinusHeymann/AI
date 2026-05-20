"""Daily-step portfolio simulation engine for the MCH backtest.

Features are progressively enabled via the ``phase`` argument to
``Simulation`` so the same code runs phases 2-8 with no branching elsewhere.

Phase gating
------------
- phase >= 2: share positions (equal-weight, $400K notional)
- phase >= 3: LEAPS long legs
- phase >= 4: covered calls (Tier 1/2) and PMCC short calls (Tier 3), with
               earnings blackout
- phase >= 5: position stop-losses, portfolio circuit breaker, correlation
               breaker
- phase >= 6: VIX OTM call tail hedge
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from . import config as C
from . import options as O
from . import synth


# --------------------------------------------------------------------------
# Position records
# --------------------------------------------------------------------------
@dataclass
class ShareLot:
    ticker: str
    shares: float
    cost_basis: float  # $/share


@dataclass
class OptionPos:
    ticker: str
    side: int                # +1 long, -1 short
    contracts: float         # 1 contract = 100 shares
    strike: float
    expiry: pd.Timestamp
    entry_price: float       # premium per share at entry
    role: str                # 'leaps', 'short_call', 'vix_hedge'
    blackout_closed: bool = False  # short call closed for earnings


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
class Simulation:
    def __init__(
        self,
        prices: pd.DataFrame,
        phase: int = 9,
        *,
        params: dict[str, Any] | None = None,
        verbose: bool = False,
    ) -> None:
        self.prices = prices
        self.phase = phase
        self.verbose = verbose
        # O(1) business-day-offset lookups. ``_bday_pos`` maps each timestamp
        # in the frame to its integer position so
        # ``_business_days_to(a, b) == bday_pos[b] - bday_pos[a]`` for dates
        # known to the simulation.
        self._bday_pos = {d: i for i, d in enumerate(prices.index)}
        self._bday_index = prices.index
        self._n_bdays = len(prices.index)
        # Numpy views for fast price lookup.
        self._price_np = prices.values
        self._price_cols = {c: i for i, c in enumerate(prices.columns)}
        # Parameter overrides for sensitivity scenarios.
        self.p = {
            "leaps_delta": C.LEAPS_DELTA_TARGET,
            "short_delta": C.SHORT_CALL_DELTA_TARGET,
            "stop_loss": C.POSITION_STOP_LOSS,
            "cb_dd": C.CIRCUIT_BREAKER_DD,
            "vix_hedge_ann": C.VIX_HEDGE_BUDGET_ANNUAL,
        }
        if params:
            self.p.update(params)

        # Realized-vol table used as IV proxy.
        self._rv = O.realized_vol(prices)
        self._rv_np = self._rv.values
        self._rv_col_idx = {c: i for i, c in enumerate(self._rv.columns)}
        self._earnings = synth.synth_earnings_calendar(prices.index)

        # State
        self.cash = C.INIT_CAPITAL
        self.lots: dict[str, ShareLot] = {}
        self.options: list[OptionPos] = []
        self.stopped_names: set[str] = set()   # names currently stopped-out
        self.stop_cool_until: dict[str, pd.Timestamp] = {}
        self.circuit_on = False
        self.correlation_on = False
        self.peak_nav = C.INIT_CAPITAL
        self.vix_budget_remaining = 0.0
        self.current_year = None

        # Audit trail
        self.nav_history: list[tuple[pd.Timestamp, float]] = []
        self.premium_collected = 0.0
        self.premium_paid = 0.0
        self.stop_events = 0
        self.circuit_events = 0
        self.corr_events = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _iv(self, ticker: str, date: pd.Timestamp) -> float:
        if ticker not in self._price_cols:
            return 0.25
        i = self._bday_pos.get(date)
        if i is None or i < C.RV_WINDOW:
            return 0.25
        rv = self._rv_np[i, self._rv_col_idx[ticker]]
        return O.iv_from_rv(rv)

    def _price(self, ticker: str, date: pd.Timestamp) -> float:
        i = self._bday_pos[date]
        return float(self._price_np[i, self._price_cols[ticker]])

    def _business_days_to(self, start: pd.Timestamp, end: pd.Timestamp) -> int:
        """O(1) offset when both dates are in the simulation grid; falls back
        to a 5/7 calendar-day approximation otherwise (used for expiries that
        land past the last business day)."""
        if end <= start:
            return 0
        i0 = self._bday_pos.get(start)
        i1 = self._bday_pos.get(end)
        if i0 is not None and i1 is not None:
            return i1 - i0
        # Fallback: calendar-day * 5/7 approximation.
        days = (end - start).days
        return max(0, int(days * 5 / 7))

    # ------------------------------------------------------------------
    # Market to market
    # ------------------------------------------------------------------
    def _nav(self, date: pd.Timestamp) -> float:
        nav = self.cash
        for lot in self.lots.values():
            nav += lot.shares * self._price(lot.ticker, date)
        for op in self.options:
            px = self._price_option(op, date)
            nav += op.side * op.contracts * 100.0 * px
        return nav

    def _price_option(self, op: OptionPos, date: pd.Timestamp) -> float:
        S = self._price(op.ticker if not op.ticker.startswith("^") else "^VIX", date)
        T = max(self._business_days_to(date, op.expiry), 0) / 252.0
        sig = self._iv(op.ticker, date) if not op.ticker.startswith("^") else 1.10
        return O.bs_call_price(S, op.strike, T, C.RISK_FREE, sig)

    # ------------------------------------------------------------------
    # Initial allocation
    # ------------------------------------------------------------------
    def _initial_allocate(self, date: pd.Timestamp) -> None:
        per_name = C.SHARES_ALLOC / len(C.TICKERS)
        for t in C.TICKERS:
            p = self._price(t, date)
            shares = per_name / p
            self.lots[t] = ShareLot(t, shares, p)
            self.cash -= shares * p

        if self.phase >= 3:
            self._open_leaps(date, first_time=True)

    def _open_leaps(self, date: pd.Timestamp, first_time: bool = False) -> None:
        """Deploy/redeploy LEAPS capital across the LEAPS universe.

        Uses fractional contracts so per-name budgets are honoured exactly
        (prices are synthetic; fractional option contracts don't exist in
        practice but remove quantisation noise from the simulation).
        """
        nav = self._nav(date)
        scale = nav / C.INIT_CAPITAL if not first_time else 1.0
        leaps_budget_total = C.LEAPS_ALLOC * scale
        per_name_budget = leaps_budget_total / len(C.LEAPS_UNIVERSE)
        for t in C.LEAPS_UNIVERSE:
            if t in self.stopped_names:
                continue
            S = self._price(t, date)
            sig = self._iv(t, date)
            T = C.LEAPS_DTE_ENTRY / 365.0
            K = O.strike_for_delta(S, T, C.RISK_FREE, sig, self.p["leaps_delta"])
            px = O.bs_call_price(S, K, T, C.RISK_FREE, sig)
            if px <= 0 or per_name_budget <= 0:
                continue
            spend = min(per_name_budget, max(self.cash * 0.95, 0.0))
            if spend <= 0:
                continue
            contracts = spend / (px * 100.0)
            if contracts <= 0:
                continue
            expiry = date + pd.tseries.offsets.BDay(C.LEAPS_DTE_ENTRY)
            self.options.append(
                OptionPos(t, +1, contracts, K, expiry, px, "leaps")
            )
            self.cash -= contracts * 100.0 * px

    def _roll_leaps(self, date: pd.Timestamp) -> None:
        """Roll LEAPS when DTE <= C.LEAPS_DTE_ROLL."""
        keep = []
        rolled = False
        for op in self.options:
            if op.role != "leaps":
                keep.append(op)
                continue
            dte = self._business_days_to(date, op.expiry)
            if dte > C.LEAPS_DTE_ROLL:
                keep.append(op)
                continue
            # Close: sell at current price
            px = self._price_option(op, date)
            self.cash += op.contracts * 100.0 * px
            rolled = True
        self.options = keep
        if rolled:
            self._open_leaps(date)

    # ------------------------------------------------------------------
    # Short-call overlay (Tier 1/2 covered, Tier 3 PMCC)
    # ------------------------------------------------------------------
    def _has_short_call(self, ticker: str) -> bool:
        return any(
            op.role == "short_call" and op.ticker == ticker
            for op in self.options
        )

    def _near_earnings(self, ticker: str, date: pd.Timestamp) -> bool:
        cal = self._earnings.get(ticker, set())
        for e in cal:
            if 0 <= (e - date).days <= C.EARNINGS_BLACKOUT_DAYS:
                return True
        return False

    def _open_short_calls(self, date: pd.Timestamp) -> None:
        overlay_universe = C.TIER_CC + C.TIER_PMCC
        for t in overlay_universe:
            if t in self.stopped_names:
                continue
            if self._has_short_call(t):
                continue
            if self._near_earnings(t, date):
                continue
            # Need backing: shares for Tier CC, LEAPS for Tier PMCC.
            backing_contracts = self._backing_contracts(t)
            if backing_contracts < 1:
                continue
            S = self._price(t, date)
            sig = self._iv(t, date)
            T = C.SHORT_CALL_DTE_ENTRY / 365.0
            K = O.strike_for_delta(S, T, C.RISK_FREE, sig, self.p["short_delta"])
            K = max(K, S * 1.01)  # never below spot
            px = O.bs_call_price(S, K, T, C.RISK_FREE, sig)
            if px <= 0:
                continue
            expiry = date + pd.tseries.offsets.BDay(C.SHORT_CALL_DTE_ENTRY)
            self.options.append(
                OptionPos(t, -1, backing_contracts, K, expiry, px, "short_call")
            )
            prem = backing_contracts * 100.0 * px
            self.cash += prem  # premium received
            self.premium_collected += prem

    def _backing_contracts(self, ticker: str) -> float:
        """Fractional backing contracts available for a short-call leg.

        Tier 1/2 (covered call): one contract per 100 shares of the lot.
        Tier 3 (PMCC): 1:1 with the long LEAPS contract count. This keeps
        the short call delta small relative to the long LEAPS delta so the
        structure remains net long as intended.
        """
        if ticker in C.TIER_CC:
            lot = self.lots.get(ticker)
            if not lot:
                return 0.0
            return lot.shares / 100.0
        if ticker in C.TIER_PMCC:
            n = 0.0
            for op in self.options:
                if op.role == "leaps" and op.ticker == ticker and op.side == +1:
                    n += op.contracts
            return n
        return 0.0

    def _manage_short_calls(self, date: pd.Timestamp) -> None:
        survivors = []
        for op in self.options:
            if op.role != "short_call":
                survivors.append(op)
                continue
            # Expired?
            if date >= op.expiry:
                # Settle: pay intrinsic (if ITM caller exercises via cash equiv).
                S = self._price(op.ticker, date)
                intrinsic = max(S - op.strike, 0.0)
                cost = op.contracts * 100.0 * intrinsic
                self.cash -= cost
                self.premium_paid += cost
                continue
            # Close early if near earnings. Drop the position entirely; a
            # new short will be opened once the blackout window clears.
            if self._near_earnings(op.ticker, date):
                px = self._price_option(op, date)
                cost = op.contracts * 100.0 * px
                self.cash -= cost
                self.premium_paid += cost
                continue
            # Close early once DTE <= threshold (capture theta decay).
            dte = self._business_days_to(date, op.expiry)
            if dte <= C.SHORT_CALL_DTE_CLOSE:
                px = self._price_option(op, date)
                cost = op.contracts * 100.0 * px
                self.cash -= cost
                self.premium_paid += cost
                continue
            survivors.append(op)
        self.options = survivors

    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------
    def _check_stop_losses(self, date: pd.Timestamp) -> None:
        for t in list(self.lots.keys()):
            lot = self.lots[t]
            S = self._price(t, date)
            if S < lot.cost_basis * (1.0 - self.p["stop_loss"]):
                # Stop out: liquidate shares and any open options on this name.
                self.cash += lot.shares * S
                del self.lots[t]
                # Close all options on this name.
                remaining = []
                for op in self.options:
                    if op.ticker == t:
                        px = self._price_option(op, date)
                        self.cash += op.side * op.contracts * 100.0 * px
                    else:
                        remaining.append(op)
                self.options = remaining
                self.stopped_names.add(t)
                self.stop_cool_until[t] = date + pd.tseries.offsets.BDay(
                    C.POSITION_STOP_COOLDOWN
                )
                self.stop_events += 1

    def _maybe_reenter(self, date: pd.Timestamp) -> None:
        for t in list(self.stopped_names):
            if date >= self.stop_cool_until.get(t, date):
                # Re-enter: repurchase per-name allocation.
                per_name = (C.SHARES_ALLOC / len(C.TICKERS)) * (self._nav(date) / C.INIT_CAPITAL)
                per_name = min(per_name, self.cash * 0.9)
                if per_name <= 0:
                    continue
                S = self._price(t, date)
                shares = per_name / S
                self.lots[t] = ShareLot(t, shares, S)
                self.cash -= shares * S
                self.stopped_names.discard(t)

    def _check_circuit_breaker(self, date: pd.Timestamp) -> None:
        nav = self._nav(date)
        self.peak_nav = max(self.peak_nav, nav)
        dd = 1.0 - nav / self.peak_nav
        if not self.circuit_on and dd >= self.p["cb_dd"]:
            self.circuit_on = True
            self.circuit_events += 1
            # De-risk: close all LEAPS and short calls, halve share exposure.
            remaining = []
            for op in self.options:
                if op.role in ("leaps", "short_call", "vix_hedge"):
                    px = self._price_option(op, date)
                    self.cash += op.side * op.contracts * 100.0 * px
                else:
                    remaining.append(op)
            self.options = remaining
            # Halve shares.
            for t, lot in list(self.lots.items()):
                sell = lot.shares * 0.5
                self.cash += sell * self._price(t, date)
                lot.shares -= sell
        elif self.circuit_on and dd <= C.CIRCUIT_BREAKER_RECOVER:
            self.circuit_on = False
            # Resume: add shares up to per-name share budget scaled by NAV,
            # then redeploy LEAPS.
            per_name = (C.SHARES_ALLOC / len(C.TICKERS)) * (nav / C.INIT_CAPITAL)
            for t, lot in list(self.lots.items()):
                S = self._price(t, date)
                current_value = lot.shares * S
                target = min(per_name, self.cash * 0.9)
                add_cash = max(target - current_value, 0)
                if add_cash > 0:
                    lot.shares += add_cash / S
                    self.cash -= add_cash
            if self.phase >= 3:
                self._open_leaps(date)

    def _check_correlation_breaker(self, date: pd.Timestamp) -> None:
        if date not in self.prices.index:
            return
        idx = self.prices.index.get_loc(date)
        if idx < C.CORRELATION_WINDOW + 1:
            return
        window = self.prices.iloc[idx - C.CORRELATION_WINDOW : idx][C.TICKERS]
        rets = window.pct_change().dropna()
        if len(rets) < 5:
            return
        corr = rets.corr().values
        n = corr.shape[0]
        off_diag = (corr.sum() - np.trace(corr)) / (n * (n - 1))
        if not self.correlation_on and off_diag > C.CORRELATION_BREAKER:
            self.correlation_on = True
            self.corr_events += 1
            # Cut overlay book (short calls) but keep shares/LEAPS.
            remaining = []
            for op in self.options:
                if op.role == "short_call":
                    px = self._price_option(op, date)
                    self.cash += op.side * op.contracts * 100.0 * px
                else:
                    remaining.append(op)
            self.options = remaining
        elif self.correlation_on and off_diag < C.CORRELATION_BREAKER - 0.1:
            self.correlation_on = False

    # ------------------------------------------------------------------
    # VIX tail hedge
    # ------------------------------------------------------------------
    def _manage_vix_hedge(self, date: pd.Timestamp) -> None:
        # Reset annual budget at each new year.
        if self.current_year != date.year:
            self.current_year = date.year
            self.vix_budget_remaining = self._nav(date) * self.p["vix_hedge_ann"]

        # Expire old hedges.
        survivors = []
        for op in self.options:
            if op.role != "vix_hedge":
                survivors.append(op)
                continue
            if date >= op.expiry:
                # Settle intrinsic
                spot = self._price("^VIX", date)
                intrinsic = max(spot - op.strike, 0.0)
                payoff = op.contracts * C.VIX_HEDGE_NOTIONAL_MULT * intrinsic
                self.cash += payoff
                continue
            survivors.append(op)
        self.options = survivors

        # Monthly reinvestment: add new hedge on first business day of month.
        if date.day <= 3 and not any(
            op.role == "vix_hedge" for op in self.options
        ):
            spot = self._price("^VIX", date)
            strike = spot + C.VIX_HEDGE_STRIKE_OFFSET
            # Price a 30d OTM VIX call roughly via BS with IV ~110% (VIX IV is
            # notoriously high).
            T = C.VIX_HEDGE_DTE / 365.0
            px = O.bs_call_price(spot, strike, T, C.RISK_FREE, 1.10)
            if px <= 0:
                return
            monthly_budget = self.vix_budget_remaining / max(1, 13 - date.month)
            contracts = monthly_budget / (px * C.VIX_HEDGE_NOTIONAL_MULT)
            if contracts <= 0 or monthly_budget <= 0:
                return
            expiry = date + pd.tseries.offsets.BDay(C.VIX_HEDGE_DTE)
            cost = contracts * C.VIX_HEDGE_NOTIONAL_MULT * px
            self.cash -= cost
            self.vix_budget_remaining -= cost
            self.options.append(
                OptionPos("^VIX", +1, contracts, strike, expiry, px, "vix_hedge")
            )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        dates = self.prices.index
        first_good = dates[C.RV_WINDOW + 1]  # wait for RV window to fill
        allocated = False

        for date in dates:
            if date < first_good:
                continue

            if not allocated:
                self._initial_allocate(date)
                allocated = True

            # Risk -----------------------------------------------------------
            if self.phase >= 5:
                self._check_stop_losses(date)
                self._maybe_reenter(date)
                self._check_circuit_breaker(date)
                self._check_correlation_breaker(date)

            # LEAPS roll -----------------------------------------------------
            if self.phase >= 3 and not self.circuit_on:
                self._roll_leaps(date)

            # Overlay --------------------------------------------------------
            if self.phase >= 4 and not self.circuit_on and not self.correlation_on:
                self._manage_short_calls(date)
                # Only open new shorts on first business day of each week.
                if date.weekday() == 0:
                    self._open_short_calls(date)

            # VIX hedge ------------------------------------------------------
            if self.phase >= 6:
                self._manage_vix_hedge(date)

            nav = self._nav(date)
            self.nav_history.append((date, nav))

        df = pd.DataFrame(self.nav_history, columns=["date", "nav"]).set_index("date")
        return df

    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        return {
            "premium_collected": self.premium_collected,
            "premium_paid": self.premium_paid,
            "stop_events": self.stop_events,
            "circuit_events": self.circuit_events,
            "corr_events": self.corr_events,
        }
