"""Metrics + report writing for the MCH backtest."""
from __future__ import annotations

import datetime as dt
import os
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def compute_metrics(nav: pd.Series, rf: float = 0.03) -> dict[str, float]:
    nav = nav.dropna()
    if len(nav) < 2:
        return {"cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "max_dd": 0.0,
                "calmar": 0.0, "end_value": float(nav.iloc[-1] if len(nav) else 0)}
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    ret = nav.pct_change().dropna()
    vol = ret.std() * np.sqrt(252)
    sharpe = (ret.mean() * 252 - rf) / vol if vol > 0 else 0.0
    running_peak = nav.cummax()
    dd = (nav / running_peak - 1.0)
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return {
        "cagr": float(cagr),
        "vol": float(vol),
        "sharpe": float(sharpe),
        "max_dd": max_dd,
        "calmar": float(calmar),
        "end_value": float(nav.iloc[-1]),
    }


# --------------------------------------------------------------------------
# Interim results
# --------------------------------------------------------------------------
def append_interim(
    phase: int,
    phase_name: str,
    nav: pd.Series | None,
    extras: dict[str, Any] | None = None,
) -> None:
    """Append a phase entry to backtest_interim_results.md."""
    path = C.INTERIM_FILE
    new_file = not os.path.exists(path)
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = []
    if new_file:
        lines.append("# MCH Backtest — Interim Results\n")
        lines.append(
            "Synthetic-data 30-year simulation. Each entry records cumulative "
            "stats up through the completed phase.\n"
        )
    lines.append(f"## Phase {phase} — {phase_name}\n")
    lines.append(f"- Timestamp (UTC): {ts}")
    if nav is not None and len(nav) > 0:
        m = compute_metrics(nav)
        lines.append(f"- Portfolio value: ${m['end_value']:,.0f}")
        lines.append(f"- CAGR: {m['cagr']*100:.2f}%")
        lines.append(f"- Annualised vol: {m['vol']*100:.2f}%")
        lines.append(f"- Sharpe (rf=3%): {m['sharpe']:.2f}")
        lines.append(f"- Max drawdown: {m['max_dd']*100:.2f}%")
        lines.append(f"- Calmar: {m['calmar']:.2f}")
    if extras:
        for k, v in extras.items():
            lines.append(f"- {k}: {v}")
    lines.append("")  # blank line
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def completed_phases() -> set[int]:
    path = C.INTERIM_FILE
    done: set[int] = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## Phase "):
                try:
                    n = int(line.split()[2])
                    done.add(n)
                except (ValueError, IndexError):
                    pass
    return done


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def ensure_chart_dir() -> None:
    os.makedirs(C.CHART_DIR, exist_ok=True)


def plot_equity_curves(curves: dict[str, pd.Series], path: str, title: str) -> None:
    ensure_chart_dir()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for name, s in curves.items():
        ax.plot(s.index, s.values, label=name, linewidth=1.2)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel("NAV (log scale, $)")
    ax.set_xlabel("Date")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_drawdowns(curves: dict[str, pd.Series], path: str, title: str) -> None:
    ensure_chart_dir()
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for name, s in curves.items():
        peak = s.cummax()
        dd = (s / peak - 1.0) * 100.0
        ax.plot(dd.index, dd.values, label=name, linewidth=1.0)
    ax.set_title(title)
    ax.set_ylabel("Drawdown (%)")
    ax.set_xlabel("Date")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_annual_returns(nav: pd.Series, path: str, title: str) -> None:
    ensure_chart_dir()
    yearly = nav.resample("YE").last().pct_change().dropna() * 100.0
    fig, ax = plt.subplots(figsize=(11, 4.5))
    colors = ["#2a9d8f" if v >= 0 else "#e76f51" for v in yearly.values]
    ax.bar(yearly.index.year, yearly.values, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(title)
    ax.set_ylabel("Annual return (%)")
    ax.set_xlabel("Year")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
