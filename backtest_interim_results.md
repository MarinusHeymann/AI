# MCH Backtest — Interim Results

Synthetic-data 30-year simulation. Each entry records cumulative stats up through the completed phase.

## Phase 1 — Data + synthetic proxies

- Timestamp (UTC): 2026-04-12 18:21:03Z
- rows: 7828
- columns: SPY, AAPL, NVDA, META, MU, GOOGL, AMZN, MSFT, NOW, HOOD, BRK.B, PANW, GLD, QQQ, TLT, ^VIX

## Phase 2 — Shares-only simulation

- Timestamp (UTC): 2026-04-12 18:21:04Z
- Portfolio value: $15,777,651
- CAGR: 10.49%
- Annualised vol: 19.52%
- Sharpe (rf=3%): 0.44
- Max drawdown: -56.16%
- Calmar: 0.19
- premium_collected: $0
- premium_paid: $0
- stop_events: 0
- circuit_events: 0
- corr_events: 0

## Phase 3 — LEAPS layer

- Timestamp (UTC): 2026-04-12 18:21:11Z
- Portfolio value: $983,651,904
- CAGR: 26.57%
- Annualised vol: 41.18%
- Sharpe (rf=3%): 0.68
- Max drawdown: -77.63%
- Calmar: 0.34
- premium_collected: $0
- premium_paid: $0
- stop_events: 0
- circuit_events: 0
- corr_events: 0

## Phase 4 — Covered call / PMCC overlay

- Timestamp (UTC): 2026-04-12 18:21:38Z
- Portfolio value: $301,870,714
- CAGR: 21.66%
- Annualised vol: 37.47%
- Sharpe (rf=3%): 0.61
- Max drawdown: -73.56%
- Calmar: 0.29
- premium_collected: $150,728,352
- premium_paid: $221,093,373
- stop_events: 0
- circuit_events: 0
- corr_events: 0

## Phase 5 — Risk management

- Timestamp (UTC): 2026-04-12 18:21:54Z
- Portfolio value: $21,483,796
- CAGR: 11.36%
- Annualised vol: 18.44%
- Sharpe (rf=3%): 0.49
- Max drawdown: -45.12%
- Calmar: 0.25
- premium_collected: $5,156,798
- premium_paid: $5,755,129
- stop_events: 39
- circuit_events: 6
- corr_events: 0

## Phase 6 — VIX tail hedge

- Timestamp (UTC): 2026-04-12 18:22:11Z
- Portfolio value: $69,002,849
- CAGR: 15.80%
- Annualised vol: 32.20%
- Sharpe (rf=3%): 0.50
- Max drawdown: -35.58%
- Calmar: 0.44
- premium_collected: $15,524,136
- premium_paid: $13,646,674
- stop_events: 39
- circuit_events: 20
- corr_events: 0

## Phase 7 — Benchmark comparison

- Timestamp (UTC): 2026-04-12 18:22:11Z
- Portfolio value: $69,002,849
- CAGR: 15.80%
- Annualised vol: 32.20%
- Sharpe (rf=3%): 0.50
- Max drawdown: -35.58%
- Calmar: 0.44
- benchmarks: SPY, QQQ, 60_40

## Phase 8 — Sensitivity scenarios

- Timestamp (UTC): 2026-04-12 18:24:31Z
- Portfolio value: $69,002,849
- CAGR: 15.80%
- Annualised vol: 32.20%
- Sharpe (rf=3%): 0.50
- Max drawdown: -35.58%
- Calmar: 0.44
- scenarios: 8

## Phase 9 — Final report

- Timestamp (UTC): 2026-04-12 18:24:32Z
- Portfolio value: $69,002,849
- CAGR: 15.80%
- Annualised vol: 32.20%
- Sharpe (rf=3%): 0.50
- Max drawdown: -35.58%
- Calmar: 0.44
- report: MCH_Backtest_Report.md

