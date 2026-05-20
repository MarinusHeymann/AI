#!/usr/bin/env python3
"""Top-level orchestrator for the MCH 30-year backtest.

Runs every phase in sequence, writing interim results after each phase and a
final Markdown report at the end. Because the work is long-running, interim
state is persisted so that a subsequent invocation can resume.
"""
from __future__ import annotations

import os
import pickle
import sys
import time
from typing import Any

import pandas as pd

# Allow running as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mch import config as C  # noqa: E402
from mch import report as R  # noqa: E402
from mch import synth  # noqa: E402
from mch.engine import Simulation  # noqa: E402


PHASE_NAMES = {
    1: "Data + synthetic proxies",
    2: "Shares-only simulation",
    3: "LEAPS layer",
    4: "Covered call / PMCC overlay",
    5: "Risk management",
    6: "VIX tail hedge",
    7: "Benchmark comparison",
    8: "Sensitivity scenarios",
    9: "Final report",
}


# --------------------------------------------------------------------------
def log(msg: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


# --------------------------------------------------------------------------
# Phase 1: data
# --------------------------------------------------------------------------
def phase1_data() -> pd.DataFrame:
    if os.path.exists(C.DATA_CACHE_FILE):
        log(f"Loading cached data from {C.DATA_CACHE_FILE}")
        with open(C.DATA_CACHE_FILE, "rb") as f:
            return pickle.load(f)
    log("Generating synthetic 30-year price paths")
    df = synth.generate_prices()
    with open(C.DATA_CACHE_FILE, "wb") as f:
        pickle.dump(df, f)
    log(f"Saved {df.shape} price frame to {C.DATA_CACHE_FILE}")
    return df


# --------------------------------------------------------------------------
# Phases 2-6: engine variants
# --------------------------------------------------------------------------
def run_phase(prices: pd.DataFrame, phase: int) -> tuple[pd.Series, dict[str, Any]]:
    log(f"Running engine for phase {phase} ({PHASE_NAMES[phase]})")
    sim = Simulation(prices, phase=phase)
    nav_df = sim.run()
    return nav_df["nav"], sim.stats()


# --------------------------------------------------------------------------
# Phase 7: benchmarks
# --------------------------------------------------------------------------
def build_benchmarks(prices: pd.DataFrame, nav_start_date: pd.Timestamp) -> dict[str, pd.Series]:
    """Construct SPY, QQQ, and 60/40 benchmark equity curves, each normalised
    to start at ``C.INIT_CAPITAL`` on ``nav_start_date``."""
    out: dict[str, pd.Series] = {}
    sub = prices.loc[nav_start_date:]
    out["SPY"] = sub["SPY"] / sub["SPY"].iloc[0] * C.INIT_CAPITAL
    out["QQQ"] = sub["QQQ"] / sub["QQQ"].iloc[0] * C.INIT_CAPITAL

    # 60/40 = 60% SPY + 40% TLT, rebalanced monthly.
    spy_r = sub["SPY"].pct_change().fillna(0.0)
    tlt_r = sub["TLT"].pct_change().fillna(0.0)
    nav = C.INIT_CAPITAL
    vals = []
    w_spy = 0.6
    for i, d in enumerate(sub.index):
        r = w_spy * spy_r.iloc[i] + (1 - w_spy) * tlt_r.iloc[i]
        nav *= 1 + r
        vals.append(nav)
        # Monthly rebalance (implicit: we recompute each day with fixed weights).
    out["60_40"] = pd.Series(vals, index=sub.index)
    return out


# --------------------------------------------------------------------------
# Phase 8: sensitivity scenarios
# --------------------------------------------------------------------------
SCENARIOS = {
    "Baseline":       {},
    "Tight stop 15%": {"stop_loss": 0.15},
    "Loose stop 35%": {"stop_loss": 0.35},
    "LEAPS 0.80\u0394": {"leaps_delta": 0.80},
    "LEAPS 0.60\u0394": {"leaps_delta": 0.60},
    "VIX hedge 3%":   {"vix_hedge_ann": 0.03},
    "No VIX hedge":   {"vix_hedge_ann": 0.0001},
    "CB @15%":        {"cb_dd": 0.15},
}


def run_sensitivity(prices: pd.DataFrame) -> dict[str, pd.Series]:
    curves: dict[str, pd.Series] = {}
    for name, params in SCENARIOS.items():
        log(f"  scenario: {name}  params={params}")
        sim = Simulation(prices, phase=9, params=params)
        curves[name] = sim.run()["nav"]
    return curves


# --------------------------------------------------------------------------
# Phase 9: final report
# --------------------------------------------------------------------------
def write_final_report(
    phase_navs: dict[int, pd.Series],
    benchmarks: dict[str, pd.Series],
    scenarios: dict[str, pd.Series],
    phase_stats: dict[int, dict[str, Any]],
) -> None:
    log("Rendering charts and writing final report")
    R.ensure_chart_dir()

    # Chart 1: phase 6 (== full strategy) vs benchmarks
    main_nav = phase_navs[6]
    curves_main = {"MCH (final)": main_nav, **benchmarks}
    R.plot_equity_curves(
        curves_main,
        os.path.join(C.CHART_DIR, "equity_vs_benchmarks.png"),
        "MCH vs benchmarks — equity curve (log scale)",
    )
    R.plot_drawdowns(
        curves_main,
        os.path.join(C.CHART_DIR, "drawdown_vs_benchmarks.png"),
        "MCH vs benchmarks — drawdown",
    )
    R.plot_annual_returns(
        main_nav,
        os.path.join(C.CHART_DIR, "mch_annual_returns.png"),
        "MCH — annual returns",
    )

    # Chart 2: phase contribution ladder (phases 2-6 only; phase 9 == phase 6)
    ladder = {p: s for p, s in phase_navs.items() if p in (2, 3, 4, 5, 6)}
    phase_curves = {f"Phase {p} — {PHASE_NAMES[p]}": s for p, s in sorted(ladder.items())}
    R.plot_equity_curves(
        phase_curves,
        os.path.join(C.CHART_DIR, "phase_ladder.png"),
        "MCH — feature ladder (each phase layers a new rule)",
    )

    # Chart 3: sensitivity scenarios
    R.plot_equity_curves(
        scenarios,
        os.path.join(C.CHART_DIR, "sensitivity.png"),
        "MCH — sensitivity scenarios",
    )

    # ------------------------------------------------------------------
    # Markdown report
    # ------------------------------------------------------------------
    def fmt_row(name: str, m: dict[str, float]) -> str:
        return (
            f"| {name} | ${m['end_value']:,.0f} | {m['cagr']*100:.2f}% | "
            f"{m['vol']*100:.2f}% | {m['sharpe']:.2f} | {m['max_dd']*100:.2f}% | "
            f"{m['calmar']:.2f} |"
        )

    lines: list[str] = []
    lines.append("# MCH Hedgefund — 30-Year Backtest Report\n")
    lines.append(
        "**Window**: 1996-04-01 \u2192 2026-04-01  \n"
        "**Starting capital**: $800,000 ($400K shares + $400K LEAPS premium)  \n"
        "**Universe**: AAPL, NVDA, META, MU, GOOGL, AMZN, MSFT, NOW, HOOD, BRK.B, "
        "PANW, GLD  \n"
        "**Data**: synthetic regime-aware price paths (sandbox has no external "
        "market-data access). The engine is real; the data is illustrative.\n"
    )

    lines.append("## Strategy rules applied\n")
    lines.append(
        "- Equal-weight 12 names for the share leg (8.33% each, under the 8–10% cap).\n"
        "- LEAPS leg (`\u0394\u2248" f"{C.LEAPS_DELTA_TARGET}" "`, ~15m DTE, roll at 8m) on all names except BRK.B / GLD.\n"
        "- **Tier 1/2 covered calls** on HOOD, MU, NOW, NVDA, PANW, GOOGL, AMZN.\n"
        "- **Tier 3 PMCC** (short call against LEAPS) on AAPL, META, MSFT.\n"
        "- **No overlay** on BRK.B and GLD.\n"
        "- Short calls closed 5 business days before each synthetic quarterly print; "
        "re-opened after the blackout window.\n"
        f"- Position stop-loss at {int(C.POSITION_STOP_LOSS*100)}% vs cost; "
        f"{C.POSITION_STOP_COOLDOWN}-day cool-down before re-entry.\n"
        f"- Portfolio circuit breaker on {int(C.CIRCUIT_BREAKER_DD*100)}% drawdown "
        f"(resume at {int(C.CIRCUIT_BREAKER_RECOVER*100)}%).\n"
        f"- Correlation breaker: 20-day mean pairwise \u03c1 \u2265 "
        f"{C.CORRELATION_BREAKER} cuts the overlay book.\n"
        f"- VIX OTM call tail hedge, budget "
        f"{C.VIX_HEDGE_BUDGET_ANNUAL*100:.1f}% NAV/year, strike spot + "
        f"${C.VIX_HEDGE_STRIKE_OFFSET:.0f}, 30-DTE.\n"
    )

    lines.append("## Headline results\n")
    lines.append("| Strategy | End value | CAGR | Vol | Sharpe | Max DD | Calmar |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    m_main = R.compute_metrics(main_nav)
    lines.append(fmt_row("**MCH (final, phase 9)**", m_main))
    for name, s in benchmarks.items():
        lines.append(fmt_row(name, R.compute_metrics(s)))
    lines.append("")

    lines.append("![Equity curves](charts/equity_vs_benchmarks.png)\n")
    lines.append("![Drawdowns](charts/drawdown_vs_benchmarks.png)\n")
    lines.append("![Annual returns](charts/mch_annual_returns.png)\n")

    lines.append("## Feature ladder (phase contributions)\n")
    lines.append(
        "Each row is the same engine with progressively more rules enabled, "
        "so the delta between adjacent rows isolates the contribution of "
        "that feature set.\n"
    )
    lines.append("| Phase | Feature added | End value | CAGR | Max DD | Sharpe |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for p in sorted(ladder.keys()):
        m = R.compute_metrics(ladder[p])
        lines.append(
            f"| {p} | {PHASE_NAMES[p]} | ${m['end_value']:,.0f} | "
            f"{m['cagr']*100:.2f}% | {m['max_dd']*100:.2f}% | {m['sharpe']:.2f} |"
        )
    lines.append("")
    lines.append("![Phase ladder](charts/phase_ladder.png)\n")

    lines.append("## Sensitivity scenarios\n")
    lines.append(
        "Each scenario overrides one parameter relative to the baseline and "
        "re-runs the full phase-9 engine.\n"
    )
    lines.append("| Scenario | End value | CAGR | Max DD | Sharpe | Calmar |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for name, s in scenarios.items():
        m = R.compute_metrics(s)
        lines.append(
            f"| {name} | ${m['end_value']:,.0f} | {m['cagr']*100:.2f}% | "
            f"{m['max_dd']*100:.2f}% | {m['sharpe']:.2f} | {m['calmar']:.2f} |"
        )
    lines.append("")
    lines.append("![Sensitivity](charts/sensitivity.png)\n")

    # Overlay stats from phase 9
    stats9 = phase_stats.get(9, {})
    if stats9:
        lines.append("## Overlay & risk events (phase 9)\n")
        lines.append(f"- Short-call premium collected: ${stats9.get('premium_collected', 0):,.0f}")
        lines.append(f"- Short-call premium paid (buybacks / settlements): ${stats9.get('premium_paid', 0):,.0f}")
        net = stats9.get("premium_collected", 0) - stats9.get("premium_paid", 0)
        lines.append(f"- Net short-call P&L: ${net:,.0f}")
        lines.append(f"- Stop-loss events: {stats9.get('stop_events', 0)}")
        lines.append(f"- Circuit-breaker trips: {stats9.get('circuit_events', 0)}")
        lines.append(f"- Correlation-breaker trips: {stats9.get('corr_events', 0)}\n")

    lines.append(
        "> **Note on the VIX-hedge-3% scenario.** The outlier return in that "
        "row is a classic synthetic-path lottery-ticket effect: over 30 "
        "years the simulation contains multiple VIX spikes (dotcom, GFC, "
        "2011, 2018, COVID, 2022) and a 3% annual budget compounds across "
        "several near-perfect payoffs. Do not read it as a realistic "
        "edge; a real implementation would pay higher IV and often see "
        "the hedge expire worthless.\n"
    )
    lines.append("## Caveats\n")
    lines.append(
        "1. **Synthetic data.** Prices were generated from a market-factor + "
        "idiosyncratic model with hand-placed regime shocks at 2000, 2008, "
        "2011, 2015, 2018, 2020, and 2022. Long-run drift and vol per name "
        "are calibrated to plausible long-run history, but the exact path is "
        "not real history. Results are illustrative of the strategy's "
        "mechanical behaviour, not of what actually would have happened.\n"
        "2. **Options pricing proxy.** All option legs (LEAPS, covered calls, "
        "PMCC short legs, VIX tail hedge) are priced with Black-Scholes using "
        "a realized-vol * 1.12 implied-vol proxy. No vol smile, no skew, no "
        "early-assignment risk.\n"
        "3. **Frictionless.** The engine does not charge commissions, bid-ask "
        "spreads, or borrow fees. These would typically subtract 1-3% of NAV "
        "per year from the options overlay.\n"
        "4. **Synthetic earnings calendar.** Four prints per name per year at "
        "stylised late-Jan/Apr/Jul/Oct dates, staggered per ticker. Good "
        "enough to exercise the blackout logic but not the real calendar.\n"
        "5. **Dividends.** GLD is assumed dividend-less; equity dividends are "
        "ignored (shares are total-return proxies via drift calibration).\n"
    )
    lines.append(
        "## How to reproduce\n"
        "```bash\n"
        "/home/user/AI/.venv/bin/python /home/user/AI/run_backtest.py\n"
        "```\n"
        "The run writes `data_cache.pkl` and `backtest_interim_results.md` on the "
        "way through and `MCH_Backtest_Report.md` + `charts/*.png` at the end. "
        "Re-running is idempotent if the cache exists.\n"
    )

    with open(C.REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Wrote final report to {C.REPORT_FILE}")


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def main() -> None:
    done = R.completed_phases()
    log(f"Resuming — phases already recorded: {sorted(done) or 'none'}")

    # Phase 1
    prices = phase1_data()
    if 1 not in done:
        R.append_interim(1, PHASE_NAMES[1], None,
                         extras={"rows": len(prices),
                                 "columns": ", ".join(prices.columns)})

    phase_navs: dict[int, pd.Series] = {}
    phase_stats: dict[int, dict[str, Any]] = {}
    for p in (2, 3, 4, 5, 6):
        nav, stats = run_phase(prices, p)
        phase_navs[p] = nav
        phase_stats[p] = stats
        if p not in done:
            R.append_interim(
                p,
                PHASE_NAMES[p],
                nav,
                extras={
                    "premium_collected": f"${stats['premium_collected']:,.0f}",
                    "premium_paid": f"${stats['premium_paid']:,.0f}",
                    "stop_events": stats["stop_events"],
                    "circuit_events": stats["circuit_events"],
                    "corr_events": stats["corr_events"],
                },
            )

    # Phase 7: benchmarks
    benchmarks = build_benchmarks(prices, phase_navs[6].index[0])
    if 7 not in done:
        R.append_interim(
            7, PHASE_NAMES[7], phase_navs[6],
            extras={"benchmarks": ", ".join(benchmarks.keys())},
        )

    # Phase 8: sensitivity
    scenarios = run_sensitivity(prices)
    if 8 not in done:
        baseline = scenarios["Baseline"]
        R.append_interim(
            8, PHASE_NAMES[8], baseline,
            extras={"scenarios": len(scenarios)},
        )

    # Phase 6 already enables every feature in the engine, so the "final"
    # strategy curve is phase_navs[6]; we don't create a redundant phase 9
    # row in the feature ladder. We still record phase 9 stats separately for
    # the overlay / risk-events section of the report.
    stats9 = phase_stats[6]
    phase_stats[9] = stats9

    write_final_report(phase_navs, benchmarks, scenarios, phase_stats)
    R.append_interim(9, PHASE_NAMES[9], phase_navs[6],
                     extras={"report": C.REPORT_FILE})
    log("All phases complete.")


if __name__ == "__main__":
    main()
