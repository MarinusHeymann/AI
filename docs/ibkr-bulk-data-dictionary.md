# Interactive Brokers — Bulk Data Inventory & Data Dictionary

**Source:** IBKR MCP connector (server v1.1.6, released 2026-07-30)
**Verified:** 2026-08-28, by calling every read endpoint live and recording actual response keys.
**Scope:** This documents the IBKR *connector* surface. It is not the full IBKR Web API / TWS API / Flex Query surface, which exposes more (see [Gaps](#7-gaps--what-ibkr-does-not-give-you-here)).

---

## 1. Executive summary

There are **three tiers** of data, and only one of them is genuinely "bulk":

| Tier | Data | Bulk-collectable? | Why |
|---|---|---|---|
| **A. Account & portfolio** | Positions, balances, trades, allocation, performance, orders, watchlists, alerts | **Yes — true bulk** | One call returns the entire set. No paging, no per-symbol loop. |
| **B. Market & reference data** | Quotes, OHLCV bars, option chains, futures ladders, contract search | **Fan-out only** | Every endpoint is keyed to a single `contract_id`. Bulk = you loop. There is no multi-symbol batch call. |
| **C. Research / thematic graph** | Themes, sectors, trends, peers, competitors, products, geography, theme-exposed ETFs | **Yes — paginated** | `get_theme_details` exposes `offset` + `total_count`, so the whole graph can be walked (e.g. 4,820 funds under one theme). |

**The single most important constraint:** `search_contracts` has **no pagination**. It reports `totals` (e.g. 2,190 matching stocks) but returns only ~20 rows and offers no offset. You therefore **cannot enumerate the tradable universe from this connector** — every bulk market-data job must start from a symbol list you already hold (your positions, your watchlists, a theme's company list, or an external index constituent file).

`contract_id` is the **universal join key** across every tier. Persist it.

---

## 2. Tier A — Account & portfolio (true bulk)

### 2.1 `get_account_summary` — one row, account-level margin & equity

No parameters. Returns a flat object.

| Field | Type | Description | Notes |
|---|---|---|---|
| `currency` | string | Base currency of the account | e.g. `USD` |
| `net_liquidation` | number | Total account value if fully liquidated | The headline NAV figure |
| `equity_with_loan_value` | number | Equity available to support margin | Equals NAV for unlevered cash/margin accounts |
| `buying_power` | number | Purchasing capacity | Typically ~4× available funds intraday on RegT margin |
| `gross_position_value` | number | Absolute market value of all positions | Longs + \|shorts\|, not netted |
| `total_cash_value` | number | Aggregate cash across currencies | Can be negative (margin loan / unsettled) |
| `available_funds` | number | Equity minus initial margin requirement | |
| `initial_margin` | number | Initial margin requirement now | |
| `maintenance_margin` | number | Maintenance margin requirement now | Breach → liquidation risk |
| `excess_liquidity` | number | Equity minus maintenance margin | The real margin-call cushion |
| `dividends` | number | Accrued dividends | |
| `leverage` | **string** | Gross position value / NAV | ⚠️ Returned as a string (`"1.0"`), not a number — cast on ingest |

**Bulk pattern:** snapshot once per day (or per intraday tick) and append with a timestamp. This is your NAV/margin time series.

### 2.2 `get_account_balances` — one row per currency

No parameters. Returns `balances[]`.

| Field | Type | Description | Notes |
|---|---|---|---|
| `currency` | string | Currency code, **plus a synthetic `BASE` row** | ⚠️ `BASE` is the consolidated base-currency view. **Filter it out before summing**, or you will double-count. |
| `cash_balance` | number | Cash held in that currency | |
| `settled_cash` | number | Settled portion of cash | Differs from `cash_balance` during T+1 settlement |
| `net_liquidation_value` | number | NAV attributable to that currency line | |
| `stock_market_value` | number | Market value of equity positions in that currency | |
| `unrealized_pnl` | number | Open P&L | |
| `realized_pnl` | number | Closed P&L for the session | |
| `exchange_rate` | number | FX rate to base currency | `1` for the base currency |

**Relevance for a ZAR-domiciled investor:** this is the only endpoint that decomposes NAV by currency and hands you the applied `exchange_rate`. It is the correct source for USD/ZAR translation effects — not a third-party FX feed.

### 2.3 `get_account_positions` — one row per open position

No parameters. Returns `positions[]`.

| Field | Type | Description | Notes |
|---|---|---|---|
| `contract_id` | integer | **Primary join key** to all market-data endpoints | |
| `contract_description` | string | Ticker or contract label | e.g. `APP`; for options, the full contract string |
| `position` | number | Signed quantity | Negative = short. Options are in contracts, not shares |
| `market_price` | number | Current price per unit | High precision (8+ dp) |
| `market_value` | number | `position × market_price × multiplier` | |
| `currency` | string | Currency of the instrument | |
| `average_price` | number | Average cost basis per unit | |
| `unrealized_pnl` | number | Open P&L since entry | |
| `daily_pnl` | number | P&L for the current session | Resets daily — capture intraday if you want the series |
| `asset_class` | string | `STK`, `OPT`, `FUT`, `FOP`, `CASH`, `BOND`, `FUND`, `CFD`, `WAR`, `IND`, `CRYPTO`, `CMDTY`, `IOPT` | |

⚠️ **Not returned:** multiplier, expiry, strike, right (call/put), sector, exchange. For options you must parse `contract_description` or re-resolve via the option endpoints. There is no `sector` field here — get sector weights from `get_pa_allocation` instead.

### 2.4 `get_account_trades` — execution-level fill history

Parameter: `period` — `TODAY`, `DAYS_7`, `DAYS_30`, `DAYS_60`, `DAYS_90`, `MONTH_TO_DATE`, `YEAR_TO_DATE`, `LAST_QUARTER`, `TWO_QUARTERS_AGO`, `THREE_QUARTERS_AGO`, `FOUR_QUARTERS_AGO`. All boundaries UTC.

| Field | Type | Description | Notes |
|---|---|---|---|
| `trade_id` | string | Unique execution ID | Format `00012dc6.6a85a817.01.01`; corporate-action rows use a `CRS:` prefix |
| `symbol` | string | Ticker | |
| `company_name` | string *(optional)* | Full legal name | ⚠️ **Absent on option rows** — null-check |
| `sec_type` | string | `STK`, `OPT`, `FUT`, … | |
| `currency` | string | Settlement currency | |
| `side` | string | `BUY` / `SELL` | |
| `size` | number | Quantity filled on this execution | |
| `price` | number | Execution price | For options, per-share (×100 for contract value) |
| `formatted_price` | string | Display-rounded price | Cosmetic — never compute on this |
| `order_type` | string | `LIMIT`, `MARKET`, `OTHER` | ⚠️ `OTHER` + `price: 0` = expiry/assignment, not a trade |
| `description` | string | Human label, e.g. `"419.6 Limit"` | |
| `trade_time` | string | ISO 8601 UTC | |
| `exchange` | string *(optional)* | Execution venue: `NYSE`, `NASDAQ`, `IBKRATS`, `DARK`, `BOX`, `SAPPHIRE`, `MERCURY` | ⚠️ **Absent on corporate-action rows** |
| `commission` | number | Commission for this fill | ⚠️ Sub-cent values appear on child fills of a split order (the parent fill carries the ~\$1 minimum) |
| `net_amount` | number | Gross consideration | Commission **not** deducted |
| `realized_pnl` | number | Realised P&L on closing fills | `0` on opening fills |
| `order_id` | integer | Parent order ID | **One order → many trade rows.** Group by `order_id` to reconstruct the order |

**Bulk depth:** the longest single window is 90 days / one calendar quarter. Historical depth caps at `FOUR_QUARTERS_AGO`, so **~15 months of execution history** is reachable — by stitching `YEAR_TO_DATE` + the four quarter buckets. Anything older must come from IBKR Flex Queries / Activity Statements, not this connector.

### 2.5 `get_account_orders` — live orders

No parameters. Returns `orders[]` (empty when no working orders — this is a *live* order book, not history).

Schema-documented fields: order ID, symbol, side, order type, status, quantity, price, and fill information.

### 2.6 `get_pa_allocation` — NAV decomposition

Parameters: `type` (`FINANCIAL_INSTRUMENT` | `ASSET_CLASS` | `SECTOR` | `REGION` | `COUNTRY` | `ALL`), optional `currency`, optional `date` (yyyymmdd string).

Structure: `allocations.<TYPE>.<long_positions|short_positions>.{ total{nav, weight}, items[{id, name, nav, weight}] }`

| Field | Type | Description | Notes |
|---|---|---|---|
| `currency` | string | Currency of the figures | |
| `realtime` | boolean | `true` = live; `false` = prior-day snapshot | ⚠️ Requesting **any non-base currency silently returns the prior trading day** with `realtime: false` |
| `items[].id` | string | Opaque internal code (`51`, `EQ`, `NORTHA`, `US`) | **Never interpret or display** — codes are not documented and not stable across dimensions |
| `items[].name` | string | Display label (`Basic Materials`, `Equities`) | Use this |
| `items[].nav` | number | NAV in that bucket | |
| `items[].weight` | number | Fraction of the bucket total | Sums to 1.0 **within each bucket independently** |

⚠️ **Three traps:**
1. `short_positions` is **absent** unless shorts exist — null-check it.
2. The long-side denominator differs by dimension (netted of shorts for `ASSET_CLASS`/`FINANCIAL_INSTRUMENT`, **gross** for `SECTOR`/`REGION`/`COUNTRY`). Do not compare weights across dimensions.
3. A negative cash balance shows up as a *short position* in the Cash bucket.

`date` must be on or after account inception (the `start` field from `get_pa_performance_all_periods`); earlier dates return an opaque non-retryable server error.

**This is the only source of sector/region/country exposure** in the connector — `get_account_positions` has no sector field.

### 2.7 `get_pa_performance_all_periods` — NAV & return time series

No parameters. **This is the highest-value bulk pull in the whole connector**: one call returns the complete daily NAV history for six windows.

| Field | Type | Description | Notes |
|---|---|---|---|
| `portfolio_measure` | string | `TWR` (time-weighted) or `MWR` (money-weighted) | Set by account configuration — **read it, don't assume** |
| `currency_type` | string | e.g. `base` | |
| `accounts.account.base_currency` | string | Base currency | |
| `accounts.account.start` / `.end` | string | Account inception / last data date (yyyymmdd) | `start` is the floor for `get_pa_allocation(date=…)` |
| `accounts.account.last_successful_update` | string | Server-side refresh timestamp | |
| `available_periods` | array | `["1D","7D","MTD","1M","YTD","1Y"]` | |
| `periods.<P>.start_date` | string | Period start (yyyymmdd) | |
| `periods.<P>.start_nav` | number | NAV at period start | ⚠️ May be `0.0` for inception-keyed periods — the true opening value is then `nav[0]` |
| `periods.<P>.cps[]` | array\<number\> | Cumulative return **as a fraction** from period start | ⚠️ `-0.106` = −10.6%, **not** −0.106% |
| `periods.<P>.nav[]` | array\<number\> | NAV series | |
| `periods.<P>.dates[]` | array\<string\> | Date series (yyyymmdd) | |
| `periods.<P>.frequency` | string | `D` = daily | |

⚠️ `cps`, `nav`, and `dates` are **parallel arrays** indexed together — zip them, don't assume row objects. For accounts younger than one year, `1Y` is identical to `YTD`.

**Bulk value:** the `1Y` block alone gives ~250 daily NAV observations in a single call. Benchmark it against `get_price_history` on SPY/QQQ for relative performance.

### 2.8 `get_order_instructions`, `get_watchlists` / `get_watchlist`, `get_alerts` / `get_alert`

| Endpoint | Returns | Key fields |
|---|---|---|
| `get_order_instructions` | `instructions[]` — saved (not live) order templates | ID, description, `contract_id_ex`, side, quantity, order type, limit price, time-in-force, `created` (ISO 8601), `expiration` (ISO 8601, optional) |
| `get_watchlists` | `watchlists[]` | `id` (string), `name`, `hash` (epoch-ms version stamp) |
| `get_watchlist(id)` | `name`, `hash`, `instruments[]` | `contract_id_ex`, `contract_description` |
| `get_alerts` | `alerts[]` summary | `status` = `ACTIVE` \| `PAUSED`; deleted alerts disappear |
| `get_alert(id)` | Full alert detail | Condition, operator, trigger value |

⚠️ Watchlist names are **not unique** (two lists can both be called "Favorites") — key on `id`, never on `name`.

**Bulk pattern:** `get_watchlists` → loop `get_watchlist` → union of `contract_id_ex` = your fan-out symbol list for Tier B.

---

## 3. Tier B — Market & reference data (per-contract fan-out)

### 3.1 `search_contracts` — symbol/name resolution

Parameter: `query` (ticker, company name, or keyword), optional `language`.

| Field | Type | Description | Notes |
|---|---|---|---|
| `results[].underlying_contract_id` | integer | The join key you need everywhere else | **Absent on bond rows** (they carry `issuer` instead) |
| `results[].exchange` | string | Primary listing exchange | |
| `results[].symbol` | string | Ticker | |
| `results[].description` | string | Company/instrument name | |
| `results[].country_code` | string | ISO country of listing | Disambiguates cross-listings (US vs MX vs CH) |
| `results[].sections[]` | array | Available security types: `{security_type: "STK"}`, `OPT`, `FUT`, `FOP`, `BAG`, `CFD`, `WAR`, `IOPT`, `IND`, `FUND`, `BOND`, `EC` | Presence of `OPT` = options exist |
| `results[].issuer` | string | Bond-issuer key (e.g. `e1432232`) | Bond rows only |
| `totals[]` | array | `{security_type, count}` for the **whole** matching set | e.g. 2,190 STK matches while ~20 rows are returned |

🚫 **Hard bulk limit:** no `offset`, no `limit`, no pagination. `totals` tells you how much you are *not* getting. Universe enumeration is impossible here.

⚠️ **Selection discipline:** a query for `AAPL` returns Direxion `AAPU`, GraniteShares `AAPB`, YieldMax `APLY` and more — all carrying `OPT` sections. Match on **exact `symbol`** and disambiguate with `country_code` + `description`. A query for `ES` returns Eversource Energy (NYSE) alongside the E-mini S&P 500 (CME).

### 3.2 `get_price_snapshot` — live quote & analytics (the widest single endpoint)

Parameters: `contract_id` (required), `exchange`, `market_data_names[]` (defaults to `['last','bid_ask']`).

🔑 **Key-casing rule — the #1 ETL trap.** Request names use underscores; **response keys use hyphens**, and the *values inside* mix three conventions:

| You request | Response key | Inner field casing |
|---|---|---|
| `option_open_interest` | `option-open-interest` | **camelCase** (`callInterest`) |
| `option_midpoint_iv` | `option-midpoint-iv` | **camelCase** (`dailyIv`, `isValid`) |
| `implied_vol` | `implied-vol` | **snake_case** (`daily_iv`, `is_valid`) |
| `underlying_today_option_volume` | `underlying-today-option-volume` | **camelCase** (`callVolume`) |

Normalise on ingest or you will silently drop columns.

#### Quote & session fields

| Request name | Response key | Inner fields | Description |
|---|---|---|---|
| `bid_ask` | `bid-ask` | `bid`, `bid_size`, `ask`, `ask_size` | Top of book. ⚠️ Can return `{}` when no quote is live. Sizes are floats |
| `last` | `last` | `price`, `ts`, `halted`, `is_close` | ⚠️ `price` is **null** when the trade printed at the prior price — only `ts` moves |
| `top_status` | `top-status` | `status` | `REALTIME` \| `DELAYED` \| `FROZEN` \| `FROZEN_DELAYED` \| `REJECT`. **Log this** — it tells you whether the row is subscription-grade |
| `open` / `high` / `low` | `open` / `high` / `low` | `open` / `high` / `low` | Current session |
| `prior_close` | `prior-close` | `price` | ⚠️ Observed **empty `{}` during the session** |
| `change` | `change` | `change`, `change_pct` | vs prior close |
| `plprice` | `plprice` | `price` | Mark price used for P&L |
| `volume` | `volume` | `volume` | ⚠️ Returned in **scientific notation** (`2.4775615514498E7`) — parse as float, not int |

#### Analytics & statistics

| Request name | Response key | Inner fields | Description |
|---|---|---|---|
| `misc_statistics` | `misc-statistics` | `high_13w`, `high_26w`, `high_52w`, `low_13w`, `low_26w`, `low_52w`, `open_52w` | Ranges — cheap way to get 52-week high/low without pulling bars |
| `historical_vol` | `historical-vol` | `daily_pct`, `annual_pct` | 30-day realised vol, **as a fraction** (0.354 = 35.4%) |
| `implied_vol_underlying` | `implied-vol-underlying` | `daily_iv`, `annual_iv`, `is_valid` | Underlying IV. Use `annual_iv`; check `is_valid` |
| `implied_volatility_percentile` | `implied-volatility-percentile` | `high_13w`, `high_26w`, `high_52w` | **IV rank/percentile** as fractions (0.195 = 19.5th pct). The core options-timing input |
| `avg_90d_usd_volume` | `avg-90d-usd-volume` | `volume` | 90-day average USD turnover — the best liquidity filter available |
| `dividend_yield` | `dividend-yield` | `yield_pct` | STK/CFD only, 1 dp |
| `year_to_date_change` | `year-to-date-change` | `change`, `change_pct` | STK and indices |
| `underlying_today_option_volume` | `underlying-today-option-volume` | `callVolume`, `putVolume` | **Today's put/call volume → put/call ratio** |
| `underlying_avg_option_volume` | `underlying-avg-option-volume` | `avgCallVolume`, `avgPutVolume` | Baseline for unusual-activity detection |
| `cumulative_perf_1d/1w/1m/ytd/1y/3y/5y` | `cumulative-perf-*` | — | ⚠️ Observed **empty `{}` for a common stock** — these are ETF/mutual-fund oriented |
| `total_net_assets` | `total-net-assets` | — | ⚠️ Empty for stocks; funds/ETFs only |

#### Contract-type specific

| Request name | Response key | Inner fields | Applies to |
|---|---|---|---|
| `option_volume` | `option-volume` | `total_cost`, `volume`, `trades` | OPT, FOP — note it includes **notional traded and trade count** |
| `option_open_interest` | `option-open-interest` | `callInterest`, `putInterest` | OPT, FOP (per-contract; the non-applicable side reads 0) |
| `option_midpoint_iv` | `option-midpoint-iv` | `dailyIv`, `annualIv`, `isValid` | OPT, FOP |
| `implied_vol` | `implied-vol` | `daily_iv`, `annual_iv`, `is_valid` | OPT, FOP |
| `future_open_interest` | `future-open-interest` | — | FUT |
| `bond_yield` | `bond-yield` | bid yield, ask yield (yield-to-worst) | BOND |
| `perpetual_futures_funding_rate` | `perpetual-futures-funding-rate` | funding rate, next funding time | Perpetual crypto futures |

🚫 **No Greeks.** Delta, gamma, theta, vega and rho are **not exposed**. You get IV and must compute Greeks yourself (Black-Scholes from `annualIv`, spot, strike, time-to-expiry, rate).

⚠️ **Behavioural notes:** one contract per call — no multi-symbol batching. Fields that time out within 10s are **silently omitted** (absence ≠ zero). Frozen and delayed-frozen prices are not supported. For **futures and futures options you MUST pass the native `exchange`** (CME, CBOT, NYMEX, COMEX, EUREX) — omitting it returns an empty response, not an error.

### 3.3 `get_price_history` — OHLCV bars

Parameters: `contract_id`, `security_type`, `step`, `outside_rth` (all required), plus **either** `period` **or** `step_count` (mutually exclusive), optional `exchange`, `include_corporate_actions`.

- `step`: `THIRTY_SECS`, `ONE_MIN`, `TWO_MINS`, `FIVE_MINS`, `TEN_MINS`, `FIFTEEN_MINS`, `THIRTY_MINS`, `ONE_HOUR`, `TWO_HOURS`, `FOUR_HOURS`, `ONE_DAY`, `ONE_WEEK`, `ONE_MONTH`
- `period`: `ONE_DAY` → `FIVE_YEARS`
- `security_type`: `STK`, `OPT`, `FUT`, `FOP`, `CASH`, `WAR`, `BOND`, `CFD`, `FUND`, `IND`, `CRYPTO`, `CMDTY`, `IOPT`

| Field | Type | Description | Notes |
|---|---|---|---|
| `chart_step` | integer | Bar size **in seconds** (86400 = daily) | |
| `chart_start` / `chart_end` | string | ISO 8601 window actually served | ⚠️ Compare against what you asked for — this is how you detect server-side truncation |
| `expires` | string | Cache expiry of this response | |
| `source` | string | Price basis, e.g. `Last` | Trades, not midpoint |
| `time[]` | array\<string\> | ISO 8601 bar timestamps (UTC) | Bar **open** time |
| `open[]`, `high[]`, `low[]`, `close[]` | array\<number\> | OHLC | |
| `volume[]` | array\<number\> | Volume | |

⚠️ **Column-oriented, not row-oriented.** Six parallel arrays — zip by index. This is the opposite layout from every other endpoint.

⚠️ Corporate actions appear **only when `include_corporate_actions: true` and actions exist** in the window — the key is absent otherwise. Bars are **not split/dividend-adjusted retroactively by default**; validate against a known split before building long histories.

⚠️ Intraday depth limits (how far back `THIRTY_SECS`/`ONE_MIN` bars are actually available) were **not verified in this session** and follow IBKR's standard historical-data limits. Probe empirically per `step` and check `chart_start`.

### 3.4 `get_option_parameters` → `get_option_data` — option chains

**Step 1 — `get_option_parameters(underlying_contract_id, option_sec_type)`**

| Field | Type | Description | Notes |
|---|---|---|---|
| `exchanges[]` | array\<string\> | Valid option exchanges (`SMART`, `IBUSOPT`) | |
| `current_exchange` | string | Default/preferred exchange | |
| `expirations[].id` | string | Opaque expiration key, e.g. `265598@SMART/OPT/SMART/20260918/AAPL/1` | **Pass verbatim. Never construct** |
| `expirations[].date` | string | `YYYYMMDD` | ⚠️ **Not unique** — see below |
| `expirations[].trading_class` | string | `AAPL` vs `2AAPL`; for futures options `ES` vs `EW3` | |
| `expirations[].regular` | boolean | `true` = standard monthly; `false` = weekly / daily / 0DTE | |
| `current_expiration` | string | ID of the first regular expiration | |

⚠️ **A single `date` can carry multiple `trading_class` values that are genuinely different contracts** (e.g. `20260918` appears as both `AAPL` and `2AAPL`). Always key on `id`, never on `date`.

**Step 2 — `get_option_data(expiration_id, min_strike, max_strike)`**

| Field | Type | Description | Notes |
|---|---|---|---|
| `currency` | string | Top-level, e.g. `USD` | |
| `exchange` | string | Top-level, e.g. `SMART` | **Pass this into `get_price_snapshot`** |
| `contracts[].strike` | **string** | Strike price | ⚠️ String (`"317.5"`), not a number |
| `contracts[].call_contract_id` / `put_contract_id` | integer | Numeric IDs → `get_price_snapshot` / `get_price_history` | |
| `contracts[].call_contract_id_ex` / `put_contract_id_ex` | string | Full IDs (`838696561@SMART`) → `create_order_instruction`, `get_combo_identifier` | |
| `contracts[].call_description` / `put_description` | string | `AAPL SEP 18 '26 315 Call`; futures options append the multiplier, e.g. `(50)` | The only place the multiplier surfaces |

🚫 **The chain returns contract structure only — no prices, no IV, no open interest, no volume.** Building a full priced chain is therefore **N+1 calls**: 1 chain call + 1 `get_price_snapshot` per strike per side. A 20-strike chain both sides = **41 calls**. Bound `min_strike`/`max_strike` around spot; an unbounded chain on a liquid name returns hundreds of rows.

### 3.5 `search_futures` — futures term structure

Parameters: `underlying_contract_id`, `include_expired`, `representative_only`.

| Field | Type | Description | Notes |
|---|---|---|---|
| `contracts[].contract_id` | integer | Numeric ID → snapshot/history | |
| `contracts[].contract_id_ex` | string | Full ID (`515416632@CME`) → order instructions | Not valid as a combo leg |
| `contracts[].exchange` | string | Native exchange (`CME`) | **Required** for market data on futures |
| `contracts[].symbol` | string | Contract code (observed per-expiry: `ESZ6`, `ESU7`) | Connector docs warn this can repeat across expiries — **key on `contract_month` / `last_trading_date`**, and do not display `symbol` as the identifier |
| `contracts[].contract_month` | string | `YYYYMM` | |
| `contracts[].last_trading_date` | string | `YYYYMMDD` | |

⚠️ **Results are not sorted by expiry** — sort by `contract_month` ascending yourself. The earliest non-expired entry may be days from roll. Set `include_expired: true` for backtest work; `representative_only: false` for the full raw ladder.

**Bulk value:** one call = the entire curve (21 ES expiries out to 2031). Snapshot each leg for a term-structure/contango dataset.

---

## 4. Tier C — Research & thematic graph (paginated bulk)

### 4.1 `search_investment_topics` — theme discovery

| Field | Type | Description |
|---|---|---|
| `themes[].key` | string | UUID — pass verbatim to `get_theme_details`. **Never construct** |
| `themes[].name` | string | e.g. `Battery Materials` |

⚠️ Keyword matcher is narrow: use **short singular nouns** (`battery`, not `batteries`; `robot`, not `robotics companies`).

### 4.2 `get_theme_details` — **the one genuinely enumerable research dataset**

Parameters: `key`, `max`, `offset`, `max_funds`.

| Field | Type | Description | Notes |
|---|---|---|---|
| `name`, `description` | string | Theme identity | |
| `total_count` | integer | Total companies in theme (e.g. 67) | **Paginate with `offset` + `max` until `offset >= total_count`** |
| `available_periods[]` | array | `["1M","3M","6M","1Y"]` | |
| `linked_companies[].rank` | integer | Relevance rank — **1 = most central** | ⚠️ Relevance-ranked, **not** market-cap weighted |
| `linked_companies[].key` | string | **ISIN** (e.g. `CNE100003662`) | Companies keyed by ISIN, themes by UUID |
| `linked_companies[].contract_id` | integer | → feeds straight back into Tier B | |
| `linked_companies[].symbol`, `.exchange`, `.asset_type` | string | Instrument identity | |
| `linked_companies[].description` | string | Why it belongs to the theme | |
| `linked_companies[].evidence` | string | **Long-form sourced narrative** with revenue splits, segment %, capex | Genuinely substantive — several hundred words per company |
| `funds[].contract_id`, `.name`, `.symbol`, `.exchange` | — | ETFs/funds with theme exposure | Only when `max_funds > 0` |
| `funds[].rank_adjusted_weight` | number | Theme exposure weight | |
| `funds[].top_holdings_for_theme[]` | array | `{contract_id, name, symbol}` | |
| `total_funds_count` | integer | e.g. 4,820 | |

**This is the connector's best bulk research asset:** walk `search_investment_topics` → `get_theme_details` with pagination → you have a themed universe with `contract_id`s ready for Tier B fan-out. It also solves the universe-enumeration problem that `search_contracts` cannot.

### 4.3 `get_company_connections` — full company profile graph

Parameters: `contract_id`, `link_types[]`, `include[]` (`link_info`, `company_info`), `max`.

Returns `name`, `symbol`, `description` (full business description), `contract_id`, `exchange`, and `groups[]` where each group has `title`, `type`, and `links[]`:

| Group `type` | Contains | Link fields |
|---|---|---|
| `company_theme` | Investment theme exposure | `key`, `name`, `rank`, `description`, `evidence` |
| `company_product` | Brands & products | `key`, `name`, `rank`, `description`, `evidence` (with revenue contribution %) |
| `company_competitor` | Named competitors | `key` (**ISIN**), `name`, `contract_id`, `symbol`, `exchange`, `description` |
| `company_country` | Country exposure | `key` (ISO), `name`, `rank`, `description`, `evidence` |
| `company_region` | Region exposure | `key`, `name`, `rank`, `description`, `evidence` |

⚠️ Competitor links carry a `contract_id` → **the graph is traversable**. Peer-set expansion is a breadth-first walk.

### 4.4 `get_company_themes` — lightweight sector/trend + ranked peers

Parameters: `contract_id`, `max_themes`, `max_companies`.

Returns `linked_themes[]` with `name`, `key`, `description`, `total_count`, and `linked_companies[]` (`rank`, `name`, `key` = ISIN, `contract_id`, `symbol`, `exchange`, `asset_type`, `description`, `evidence`).

Use this over `get_company_connections` when you only need sectors/trends + peers. Use `get_company_connections` for products, geography, competitors, or evidence.

---

## 5. Join keys & identifier formats

| Identifier | Format | Produced by | Consumed by |
|---|---|---|---|
| `contract_id` | integer, e.g. `265598` | `search_contracts`, positions, option chains, futures, themes | `get_price_snapshot`, `get_price_history`, `get_option_parameters`, `get_company_*` |
| `contract_id_ex` | `<id>@<exchange>`, e.g. `838696561@SMART` | option chains, futures, watchlists | order instructions, combos, watchlist edits |
| `expiration_id` | `265598@SMART/OPT/SMART/20260918/AAPL/1` | `get_option_parameters` | `get_option_data` |
| Theme `key` | UUID | `search_investment_topics`, `get_company_themes` | `get_theme_details` |
| Company `key` | **ISIN**, e.g. `US0378331005` | theme/connection endpoints | External reconciliation (not accepted as input) |
| `order_id` | integer | `get_account_trades` | Grouping fills into orders |

**Rule:** every opaque ID (`expiration_id`, theme `key`, allocation `items[].id`) must be passed **verbatim**. None are constructible, and none should be displayed to a human.

---

## 6. Bulk collection playbook

**Daily portfolio snapshot — 5 calls, complete state:**
```
get_account_summary                  → 1 row  (NAV, margin, leverage)
get_account_balances                 → n rows (per currency + BASE)
get_account_positions                → n rows (holdings, keyed by contract_id)
get_pa_allocation(type=ALL)          → 5 dimensions in one call
get_pa_performance_all_periods       → ~250 daily NAV points
```

**Execution history backfill — 5 calls, ~15 months:**
```
YEAR_TO_DATE + LAST_QUARTER + TWO_QUARTERS_AGO + THREE_QUARTERS_AGO + FOUR_QUARTERS_AGO
→ de-duplicate on trade_id (windows overlap)
```

**Market-data fan-out — N calls, one per contract:**
```
seed list  ← positions ∪ watchlists ∪ theme companies
for each contract_id:
    get_price_snapshot(contract_id, market_data_names=[...])   # 1 call
    get_price_history(contract_id, step=ONE_DAY, period=ONE_YEAR)  # 1 call
```

**Option surface — expensive, budget for it:**
```
get_option_parameters(underlying)                    #  1 call
get_option_data(expiration_id, min_strike, max_strike)  #  1 call per expiry
get_price_snapshot(strike_contract_id)               #  1 call per strike per side  ← the cost
```
A 3-expiry × 20-strike surface ≈ **124 calls**. Bound strikes tightly and cache.

**Practical guardrails**
- Persist `contract_id` as the primary key in every table; everything else is a label that can change.
- Record `top_status` alongside every quote — a `DELAYED` row is not comparable to a `REALTIME` one.
- Treat **absent fields as unknown, never as zero** — fields that time out within 10s are silently dropped.
- Normalise the mixed key casing (`callInterest` vs `daily_iv`) at the ingest boundary, not downstream.
- Cast `leverage` (string) and `strike` (string) to numeric; parse `volume` as float (scientific notation).
- No documented rate limit is published for this connector — throttle fan-out loops conservatively and back off on empty responses.

---

## 7. Gaps — what IBKR does *not* give you here

| Not available | Consequence | Where to get it in this workspace |
|---|---|---|
| **Fundamentals** (income statement, balance sheet, cash flow, ratios) | No valuation work from IBKR data alone | Alpha Vantage (`INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`, `COMPANY_OVERVIEW`) |
| **Option Greeks** (delta/gamma/theta/vega) | Must compute from IV + spot + strike + tenor | Alpha Vantage `REALTIME_OPTIONS` / `HISTORICAL_OPTIONS`, or compute locally |
| **Earnings dates, calendars, transcripts** | No event awareness | Quartr (events, transcripts); Alpha Vantage `EARNINGS_CALENDAR` |
| **News & sentiment** | No narrative layer | Alpha Vantage `NEWS_SENTIMENT` |
| **Analyst estimates, dividends/splits history** | No forward consensus | Alpha Vantage `EARNINGS_ESTIMATES`, `DIVIDENDS`, `SPLITS` |
| **Universe enumeration / screening** | Cannot list all US equities | External constituent file, or walk `get_theme_details` |
| **Level 2 depth, tick-by-tick, streaming** | Snapshot-only, top-of-book | Full IBKR Web API / TWS API |
| **Execution history beyond ~15 months** | Limited tax/audit reconstruction | IBKR Flex Queries / Activity Statements |
| **Realised P&L by tax lot** | Only per-fill `realized_pnl` | IBKR Activity Statements |

**Positioning:** IBKR is the authoritative source for **your own account** (positions, cost basis, P&L, NAV history, allocation) and for **contract/market structure** (chains, ladders, live quotes, IV percentile). It is not a fundamentals or news provider — pair it with Alpha Vantage and Quartr rather than trying to force it into that role.
