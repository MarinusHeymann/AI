"""Build an example of the future AAPL report page under the analytical-foundation design.

Every figure is carried from the live hub page (aapl-research-2026.html, run 6 Oct 2026,
prices 5 Oct 2026). Values the new pipeline would produce but today's page does not have
are rendered as an explicit placeholder, never estimated here.

Usage: python3 build_aapl_example.py  ->  AAPL_future_report_example.html
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "AAPL_future_report_example.html")

SPOT = 333.0
PEND = '<span class="pend" title="Produced by the new pipeline; not available on today\'s page">◌ at build</span>'

# Role palette (validated: reference categorical slots 1-4, light and dark)
ROLE = {"P": ("Primary", "var(--s1)"), "S": ("Secondary", "var(--s2)"), "D": ("Distribution layer", "var(--s3)"), "X": ("Cross-check", "var(--s4)")}


def e(s):
    return html.escape(str(s), quote=True)


def pct(v):
    return f"{(v / SPOT - 1) * 100:+.0f}%"


# ---------------------------------------------------------------------------
# Chart 1: valuation dot-range (C11)
# ---------------------------------------------------------------------------
def x_of(v, lo=140, hi=360, x0=210, x1=700):
    return x0 + (v - lo) / (hi - lo) * (x1 - x0)


def valuation_chart():
    rows = [
        ("M16 Sum-of-the-parts", "P", 228, (184, 271), "Services multiple 19.6x-36.4x"),
        ("M01 Forward P/E re-rate", "P", None, None, ""),
        ("M03 EV/EBITDA", "P", None, None, ""),
        ("M05 DCF (exit multiple)", "S", 192, None, "WACC 8.5%, 22x terminal"),
        ("M02 Peer P/E re-rate", "S", 225, None, "peer median 26.5x"),
        ("M19 Scenario PWEV", "D", 269, (166, 342), "scenario range"),
        ("M20 Monte Carlo median", "D", 229, (149, 319), "P10-P90"),
        ("M22 52-week centre", "X", 290, (243, 345), "52-week range"),
    ]
    rh, top = 30, 34
    h = top + rh * len(rows) + 34
    out = [f'<svg class="chart" viewBox="0 0 720 {h}" role="img" aria-labelledby="vt vd">',
           '<title id="vt">Fair value by method versus spot</title>',
           '<desc id="vd">Every available primary and secondary anchor sits between $192 and $228, 32 to 42 percent below the $333 spot.</desc>']
    for t in (150, 200, 250, 300, 350):
        x = x_of(t)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{h - 26}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 10}" class="tick" text-anchor="middle">${t}</text>')
    xs = x_of(SPOT)
    out.append(f'<line x1="{xs:.1f}" x2="{xs:.1f}" y1="{top - 14}" y2="{h - 26}" class="ref"/>')
    out.append(f'<text x="{xs:.1f}" y="{top - 18}" class="reflabel" text-anchor="middle">Spot $333</text>')
    xf = x_of(225)
    out.append(f'<line x1="{xf:.1f}" x2="{xf:.1f}" y1="{top - 14}" y2="{h - 26}" class="ref2"/>')
    out.append(f'<text x="{xf:.1f}" y="{top - 18}" class="reflabel muted" text-anchor="middle">Production FV $225</text>')
    for i, (name, role, v, rng, note) in enumerate(rows):
        y = top + rh * i + rh / 2
        rname, col = ROLE[role]
        out.append(f'<text x="0" y="{y + 4:.1f}" class="rowlab">{e(name)}</text>')
        if v is None:
            out.append(f'<text x="{x_of(150):.1f}" y="{y + 4:.1f}" class="pendtxt">◌ computed at build (not on today\'s page)</text>')
            continue
        tip = f"{name} ({rname}): ${v} ({pct(v)} vs spot)" + (f"; {note} ${rng[0]}-${rng[1]}" if rng else (f"; {note}" if note else ""))
        g = [f'<g class="mark"><title>{e(tip)}</title>']
        if rng:
            g.append(f'<line x1="{x_of(rng[0]):.1f}" x2="{x_of(rng[1]):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2" stroke-linecap="round" opacity="0.55"/>')
        g.append(f'<circle cx="{x_of(v):.1f}" cy="{y:.1f}" r="6" fill="{col}" class="dot"/>')
        g.append(f'<rect x="{x_of(140):.1f}" y="{y - rh / 2:.1f}" width="{x_of(360) - x_of(140):.1f}" height="{rh}" fill="transparent"/>')
        g.append("</g>")
        out.extend(g)
        out.append(f'<text x="{x_of(v) + 10:.1f}" y="{y - 7:.1f}" class="val">${v} <tspan class="muted">{pct(v)}</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Chart 2: scenario returns (C12) - diverging from zero
# ---------------------------------------------------------------------------
SCEN = [  # name, prob, target, iPhone units, Services growth, op margin, multiple
    ("Structural Impairment", 0.20, 166, "declining", "~5%", "~27%", "~10x"),
    ("Recession / Capex Bear", 0.15, 220, "flat-to-down", "~8%", "~29%", "~14x"),
    ("Base", 0.35, 298, "flat", "~12%", "~31%", "~18x"),
    ("ME Bull", 0.30, 342, "up (AI-led)", "~15%", "~33%", "~24x"),
]


def scenario_chart():
    lo, hi = -60, 20
    x0, x1 = 300, 700

    def xr(r):
        return x0 + (r - lo) / (hi - lo) * (x1 - x0)

    rh, top = 34, 14
    h = top + rh * len(SCEN) + 30
    out = [f'<svg class="chart" viewBox="0 0 720 {h}" role="img" aria-label="Scenario return versus spot, with probabilities">']
    for t in (-60, -40, -20, 0, 20):
        x = xr(t)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 4}" y2="{h - 22}" class="{"axis0" if t == 0 else "grid"}"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 6}" class="tick" text-anchor="middle">{t:+d}%</text>')
    for i, (n, p, tgt, *_r) in enumerate(SCEN):
        r = (tgt / SPOT - 1) * 100
        y = top + rh * i + rh / 2
        xa, xb = (xr(r), xr(0)) if r < 0 else (xr(0), xr(r))
        col = "var(--negv)" if r < 0 else "var(--posv)"
        w = max(xb - xa, 2)
        rad = 4
        # rounded data-end, square at baseline
        if r < 0:
            path = f"M{xb:.1f},{y - 11:.1f} H{xa + rad:.1f} Q{xa:.1f},{y - 11:.1f} {xa:.1f},{y - 11 + rad:.1f} V{y + 11 - rad:.1f} Q{xa:.1f},{y + 11:.1f} {xa + rad:.1f},{y + 11:.1f} H{xb:.1f} Z"
        else:
            path = f"M{xa:.1f},{y - 11:.1f} H{xb - rad:.1f} Q{xb:.1f},{y - 11:.1f} {xb:.1f},{y - 11 + rad:.1f} V{y + 11 - rad:.1f} Q{xb:.1f},{y + 11:.1f} {xb - rad:.1f},{y + 11:.1f} H{xa:.1f} Z"
        out.append(f'<g class="mark"><title>{e(n)}: probability {p:.0%}, target ${tgt}, {r:+.0f}% vs spot</title><path d="{path}" fill="{col}"/>'
                   f'<rect x="{x0}" y="{y - rh / 2:.1f}" width="{x1 - x0}" height="{rh}" fill="transparent"/></g>')
        out.append(f'<text x="0" y="{y + 4:.1f}" class="rowlab">{e(n)} <tspan class="muted">· {p:.0%}</tspan></text>')
        lx = xa - 6 if r < 0 else xb + 6
        anchor = "end" if r < 0 else "start"
        out.append(f'<text x="{lx:.1f}" y="{y + 4:.1f}" class="val" text-anchor="{anchor}">${tgt} ({r:+.0f}%)</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Chart 3: Monte Carlo range (C13)
# ---------------------------------------------------------------------------
def mc_chart():
    h = 104
    out = [f'<svg class="chart" viewBox="0 0 720 {h}" role="img" aria-label="Monte Carlo P10 to P90 range against spot">']
    for t in (150, 200, 250, 300, 350):
        x = x_of(t, x0=40)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="22" y2="76" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="98" class="tick" text-anchor="middle">${t}</text>')
    a, b, m = x_of(149, x0=40), x_of(319, x0=40), x_of(229, x0=40)
    out.append(f'<g class="mark"><title>Monte Carlo (10,000 paths): P10 $149, median $229, P90 $319; 7% of paths finish above spot</title>'
               f'<rect x="{a:.1f}" y="34" width="{b - a:.1f}" height="20" rx="4" fill="var(--s3)" opacity="0.22"/>'
               f'<line x1="{m:.1f}" x2="{m:.1f}" y1="30" y2="58" stroke="var(--s3)" stroke-width="3"/></g>')
    out.append(f'<text x="{a:.1f}" y="72" class="val" text-anchor="start">P10 $149</text>')
    out.append(f'<text x="{b:.1f}" y="72" class="val" text-anchor="end">P90 $319</text>')
    out.append(f'<text x="{m:.1f}" y="26" class="val" text-anchor="middle">median $229</text>')
    xs = x_of(SPOT, x0=40)
    out.append(f'<line x1="{xs:.1f}" x2="{xs:.1f}" y1="16" y2="76" class="ref"/>')
    out.append(f'<text x="{xs - 4:.1f}" y="14" class="reflabel" text-anchor="end">Spot $333 · 7% of paths above</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Chart 4: tornado (C14)
# ---------------------------------------------------------------------------
TORNADO = [("Revenue CAGR ±3pp", 169, 219, 50), ("Terminal multiple ±15%", 170, 215, 46), ("Operating margin ±3pp", 175, 210, 35),
           ("WACC ±1pp", 185, 201, 16), ("Capex intensity ±15%", 189, 196, 6)]


def tornado_chart():
    lo, hi, x0, x1 = 150, 240, 170, 440

    def xv(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    rh, top = 30, 12
    h = top + rh * len(TORNADO) + 28
    out = [f'<svg class="chart" viewBox="0 0 480 {h}" role="img" aria-label="DCF per share swing by driver">']
    for t in (160, 180, 200, 220, 240):
        out.append(f'<line x1="{xv(t):.1f}" x2="{xv(t):.1f}" y1="{top - 2}" y2="{h - 22}" class="grid"/>')
        out.append(f'<text x="{xv(t):.1f}" y="{h - 6}" class="tick" text-anchor="middle">${t}</text>')
    xb = xv(192)
    out.append(f'<line x1="{xb:.1f}" x2="{xb:.1f}" y1="{top - 2}" y2="{h - 22}" class="axis0"/>')
    for i, (n, l, hgh, sw) in enumerate(TORNADO):
        y = top + rh * i + rh / 2
        out.append(f'<g class="mark"><title>{e(n)}: ${l} to ${hgh} (swing ${sw})</title>'
                   f'<rect x="{xv(l):.1f}" y="{y - 9:.1f}" width="{xb - xv(l) - 1:.1f}" height="18" rx="3" fill="var(--negv)"/>'
                   f'<rect x="{xb + 1:.1f}" y="{y - 9:.1f}" width="{xv(hgh) - xb - 1:.1f}" height="18" rx="3" fill="var(--posv)"/>'
                   f'<rect x="{x0}" y="{y - rh / 2:.1f}" width="{x1 - x0}" height="{rh}" fill="transparent"/></g>')
        out.append(f'<text x="0" y="{y + 4:.1f}" class="rowlab">{e(n)}</text>')
        out.append(f'<text x="{xv(l) - 5:.1f}" y="{y + 4:.1f}" class="val" text-anchor="end">${l}</text>')
        out.append(f'<text x="{xv(hgh) + 5:.1f}" y="{y + 4:.1f}" class="val">${hgh}</text>')
    out.append(f'<text x="{xb:.1f}" y="{top - 4}" class="reflabel" text-anchor="middle">base $192</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Chart 5: SOTP segment contributions (M16)
# ---------------------------------------------------------------------------
SEG = [  # name, revenue $bn, mix, growth, op margin (est), EBIT (est) $bn, multiple, archetype
    ("Services", 110, "26%", "+12%", "70%", 77.0, 28.0, "AR02-type platform (App Store, licensing, ads, subscriptions)"),
    ("iPhone", 210, "49%", "+2%", "35%", 73.5, 12.0, "AR05 hardware"),
    ("Wearables, Home & Accessories", 38, "9%", "-1%", "33%", 12.5, 9.0, "AR05 hardware"),
    ("Mac", 32, "7%", "+3%", "32%", 10.2, 9.0, "AR05 hardware"),
    ("iPad", 28, "6%", "+1%", "31%", 8.7, 8.0, "AR05 hardware"),
]


def sotp_chart():
    vals = [(s[0], s[5] * s[6]) for s in SEG]
    tot = sum(v for _, v in vals)
    mx = 2400
    x0, x1 = 230, 640
    rh, top = 30, 10
    h = top + rh * len(vals) + 28
    out = [f'<svg class="chart" viewBox="0 0 720 {h}" role="img" aria-label="Segment value at page multiples, billions of dollars">']
    for t in (0, 500, 1000, 1500, 2000):
        x = x0 + t / mx * (x1 - x0)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 2}" y2="{h - 22}" class="{"axis0" if t == 0 else "grid"}"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 6}" class="tick" text-anchor="middle">${t:,}bn</text>')
    for i, (n, v) in enumerate(vals):
        y = top + rh * i + rh / 2
        w = v / mx * (x1 - x0)
        out.append(f'<g class="mark"><title>{e(n)}: EBIT (est.) x multiple = ${v:,.0f}bn ({v / tot:.0%} of segment value)</title>'
                   f'<path d="M{x0},{y - 10:.1f} H{x0 + w - 4:.1f} Q{x0 + w:.1f},{y - 10:.1f} {x0 + w:.1f},{y - 6:.1f} V{y + 6:.1f} Q{x0 + w:.1f},{y + 10:.1f} {x0 + w - 4:.1f},{y + 10:.1f} H{x0} Z" fill="var(--s1)"/>'
                   f'<rect x="{x0}" y="{y - rh / 2:.1f}" width="{x1 - x0}" height="{rh}" fill="transparent"/></g>')
        out.append(f'<text x="0" y="{y + 4:.1f}" class="rowlab">{e(n)}</text>')
        out.append(f'<text x="{x0 + w + 6:.1f}" y="{y + 4:.1f}" class="val">${v:,.0f}bn <tspan class="muted">{v / tot:.0%}</tspan></text>')
    out.append("</svg>")
    return "\n".join(out), tot, vals[0][1] / tot


# ---------------------------------------------------------------------------
# Sensitivity heatmap (C14) - sequential single-hue ramp, values printed (table view)
# ---------------------------------------------------------------------------
GRID_ROWS = ["-3.0pp", "-1.5pp", "+0.0pp", "+1.5pp", "+3.0pp"]
GRID = [[154, 161, 169, 177, 184], [164, 172, 180, 189, 197], [175, 184, 192, 201, 210], [187, 196, 205, 215, 224], [199, 209, 219, 229, 238]]
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab"]


def heatmap():
    lo, hi = 154, 238
    rows = []
    for rl, row in zip(GRID_ROWS, GRID):
        cells = []
        for j, v in enumerate(row):
            k = min(int((v - lo) / (hi - lo) * (len(RAMP) - 1) + 0.5), len(RAMP) - 1)
            fg = "#ffffff" if k >= 6 else "#0b0b0b"
            base = " base" if (rl == "+0.0pp" and j == 2) else ""
            cells.append(f'<td class="hm{base}" style="background:{RAMP[k]};color:{fg}" title="Revenue CAGR {rl}, margin {GRID_ROWS[j]}: ${v} ({pct(v)} vs spot)">${v}</td>')
        rows.append(f"<tr><th>{rl}</th>{''.join(cells)}</tr>")
    head = "".join(f"<th>{c}</th>" for c in GRID_ROWS)
    return (f'<table class="heat"><caption>DCF value per share - revenue CAGR change (rows) x operating-margin change (columns); base outlined</caption>'
            f'<thead><tr><th>CAGR \\ Margin</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>')


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def ann(cid, status, executor, clock):
    return (f'<div class="ann"><span class="cid">{cid}</span><span class="st st-{status.lower()}">{status}</span>'
            f'<span>{e(executor)}</span><span class="clock">{e(clock)}</span></div>')


def chip(state, text):
    icon = {"good": "✓", "watch": "◷", "pend": "◌", "flag": "⚑", "bad": "✕"}[state]
    return f'<span class="chip chip-{state}"><span aria-hidden="true">{icon}</span> {e(text)}</span>'


def build():
    sotp_svg, sotp_tot, serv_share = sotp_chart()
    seg_ebit = sum(s[5] for s in SEG)
    serv_ebit_share = SEG[0][5] / seg_ebit
    iph_ebit_share = SEG[1][5] / seg_ebit

    method_rows = [
        # group, id, name, role, value, vs spot, basis/notes
        ("Primary anchors", "M16", "Sum-of-the-parts", "P", "$228", pct(228), "Activated by SM07: Services est. EBIT is "
         f"{serv_ebit_share:.0%} and iPhone {iph_ebit_share:.0%} of segment EBIT, with different economic engines. Today's page shows this as 'illustrative, not a blend anchor'."),
        ("Primary anchors", "M01", "Forward P/E re-rate", "P", PEND, "", "House FY+1 EPS $8.50 x AR05 archetype P/E band (band pre-registered by amendment)."),
        ("Primary anchors", "M03", "EV/EBITDA", "P", PEND, "", "EBITDA of about $170bn is implied by the page's 0.34x net debt/EBITDA on $57.7bn net debt; the peer EV/EBITDA set is authored at the build."),
        ("Secondary anchors", "M05", "DCF - FCFF, exit-multiple terminal", "S", "$192 " + chip("flag", "bridge check"), pct(192),
         "WACC 8.5%, 22x terminal (81% of EV); Gordon cross-check $158. Validation flag: equity bridge adds +$55.0bn net cash while the balance sheet reports $57.7bn net debt."),
        ("Secondary anchors", "M02", "Peer P/E re-rate (quality-weighted)", "S", "$225", pct(225), "Peer median 26.5x (quality-weighted 26.8x). Under SM07, peers split by segment (see Peers)."),
        ("Distribution layer", "M19", "Scenario PWEV", "D", "$269", pct(269), "Four authored scenarios; not a separate anchor under DEC-AF-03 (shares drivers with the anchors)."),
        ("Distribution layer", "M20", "Monte Carlo (Student-t + regime)", "D", "$229 median", pct(229), "P10-P90 $149-$319; 7% of paths above spot vs 30% of scenario mass - coherence check open."),
        ("Cross-checks (0% weight)", "M21", "Market-implied expectations", "X", "34.8x", "", "Price implies 34.8x consensus EPS and roughly 4.9pp more revenue CAGR than the house case."),
        ("Cross-checks (0% weight)", "M22", "Historical range", "X", "$290 centre", pct(290), "52-week range $243-$345; spot at the 88th percentile."),
        ("Cross-checks (0% weight)", "M06", "Dividend discount", "X", PEND, "", "Payout runs at 107.5% of FCF, mostly buybacks; dividend alone is not the value driver."),
        ("Cross-checks (0% weight)", "M14", "Mid-cycle normalised earnings", "X", PEND, "", "Shown as a cross-check for the hardware cycle."),
    ]
    na_rows = [
        ("M07 Residual income / justified P/B", "NA-BOOK", "Book equity is buyback-depleted ($90.7bn of buybacks against $98.8bn of FCF in the year); book is not invested capital."),
        ("M08 P/TBV vs ROTCE", "NA-BOOK", "Bank-style balance-sheet return method; Apple is not a deposit-funded lender."),
        ("M09 Embedded value · M10 P/AFFO · M11 Property NAV · M12 Resource NAV · M13 EV/EBITDAX · M15 Rate base · M23 FRE/AUM", "NA-MECH",
         "The method models a value mechanism this business does not have (insurance liabilities, FFO, property, reserves, rate base, AUM)."),
        ("M17 Risk-adjusted pipeline NPV", "NA-PIPE", "No development-stage assets material to value."),
    ]
    inactive_rows = [
        ("M04 Growth-adjusted EV/Sales", "SM02 hyper-growth", "Not active: iPhone +2%, Services +12% - below the 25% growth threshold. Today's 'Peer EV/Revenue re-rate' ($232, 0% weight) retires from this page."),
        ("M18 Deal value / merger arbitrage", "SM05 deal pending", "Not active: no definitive agreement."),
        ("M24 Book value / liquidation floor", "SM03 / SM04", "Not active: earnings representative; net debt/EBITDA 0.34x."),
    ]
    mrows = []
    grp = None
    for g, mid, name, role, val, vs, note in method_rows:
        if g != grp:
            mrows.append(f'<tr class="grp"><td colspan="5">{e(g)}</td></tr>')
            grp = g
        rname, col = ROLE[role]
        mrows.append(f'<tr><td><span class="key" style="background:{col}"></span>{mid}</td><td>{e(name)}<span class="sub">{e(rname)}</span></td>'
                     f'<td class="num">{val}</td><td class="num">{vs}</td><td class="note">{e(note)}</td></tr>')
    na_html = "".join(f"<tr><td>{e(n)}</td><td><code>{c}</code></td><td>{e(r)}</td></tr>" for n, c, r in na_rows)
    inact_html = "".join(f"<tr><td>{e(n)}</td><td>{e(m)}</td><td>{e(r)}</td></tr>" for n, m, r in inactive_rows)

    scen_rows = "".join(f'<tr><td>{e(n)}</td><td class="num">{p:.0%}</td><td>{e(u)}</td><td class="num">{s}</td><td class="num">{m}</td><td class="num">{mu}</td>'
                        f'<td class="num">${t}</td><td class="num">{pct(t)}</td></tr>' for n, p, t, u, s, m, mu in SCEN)
    seg_rows = "".join(f'<tr><td>{e(s[0])}</td><td class="num">${s[1]}bn</td><td class="num">{s[2]}</td><td class="num">{s[3]}</td><td class="num">{s[4]}</td>'
                       f'<td class="num">${s[5]}bn</td><td class="num">{s[6]:.1f}x</td><td>{e(s[7])}</td></tr>' for s in SEG)

    assumptions = [
        # id, driver, value, range, units, period, label, source, depends, reviewed, invalidation, status
        ("AAPL-SVC-G", "Services revenue growth", "12%", "5%-15%", "% y/y", "FY+1", "Estimate", "MCH segment model; scenario drivers", "Services value (M16); revenue", "2026-08-16",
         "< 10% for 2 consecutive prints", ("good", "Not breached · 2pp")),
        ("AAPL-IPH-G", "iPhone revenue growth", "+2%", "declining to up (AI-led)", "% y/y", "FY+1", "Estimate", "MCH segment model", "Hardware value (M16); revenue", "2026-08-16",
         "< -1% for 2 consecutive prints", ("good", "Not breached")),
        ("AAPL-SVC-M", "Services operating margin", "70%", "-", "% (est.)", "FY+1", "Judgement", "Segment estimate (not disclosed by Apple)", "Services EBIT; SM07 test", "2026-08-16",
         "Company gross margin < 45% for 2 prints (proxy)", ("pend", "Awaiting GM data")),
        ("AAPL-SVC-X", "Services EBIT multiple", "28.0x", "19.6x-36.4x", "x EBIT", "Steady state", "Judgement", "Authored; SOTP lever on page", "M16 (largest single lever)", "2026-08-16",
         "Google remedy bars the default payment", ("watch", "Event pending")),
        ("AAPL-GOOG", "Google default-search payment", "~$20bn+", "-", "$ per year", "Current", "Estimate", "Company context (authored)", "Services margin; scenarios", "2026-08-16",
         "Final US v. Google remedy curtails the payment", ("watch", "Shared with GOOGL")),
        ("AAPL-CHN", "Greater China revenue share", "~17-19%", "-", "% of revenue", "FY2025", "Fact", "FY disclosure", "Tariff / export exposure", "2026-10-05",
         "Greater China growth < -8% for 2 prints", ("pend", "Awaiting segment data")),
        ("AAPL-REV1", "House FY+1 revenue", "$465.0bn", "-", "$bn", "FY+1", "Estimate", "House model (relabelled: was 'company guidance' - D-372)", "M01, M05", "2026-10-05",
         "Consensus diverges >= 2x (D-324); today -11.9%", ("good", "Not breached")),
        ("AAPL-EPS1", "House FY+1 EPS", "$8.50", "-", "$ / share, non-GAAP", "FY+1", "Estimate", "House model (relabelled: was 'company guidance' - D-372)", "M01; forward P/E 39.2x", "2026-10-05",
         "Consensus diverges >= 2x (D-324); today -11.3%", ("good", "Not breached")),
        ("AAPL-WACC", "WACC", "8.5%", "6.5%-10.5% (grid)", "%", "Current", "Estimate", "CAPM (beta 0.80 shrunk; rf 4.51%)", "M05", "2026-10-05", "Rate deck revision (SE02)", ("good", "Current")),
        ("AAPL-TERM", "DCF terminal multiple", "22x", "15.4x-28.6x (grid)", "x FCF", "Terminal", "Judgement", "Authored for this name", "M05 (81% of EV)", "2026-08-16",
         "Peer median moves > 20%", ("good", "Current")),
        ("AAPL-SBC", "SBC dilution", "1.5% / yr", "-", "% of shares", "FY+1", "Estimate", "From SBC/revenue (~3%)", "Share count (charged once)", "2026-10-05", "SBC % revenue +2pp y/y", ("good", "Current")),
        ("AAPL-SCEN", "Scenario probabilities", "20 / 15 / 35 / 30", "-", "%", "12 months", "Judgement", "Authored scenario tree", "M19; distribution layer", "2026-08-16",
         "Reset at each scheduled reassessment; MC coherence check", ("flag", "Coherence check open")),
        ("AAPL-ND", "Net debt", "$57.7bn", "-", "$bn", "2025-09-30", "Fact", "Balance sheet via AV", "EV bridge (M03, M05, M16)", "2026-10-05", "n/a (fact)", ("flag", "Sign check vs DCF bridge")),
    ]
    arows = "".join(
        f'<tr><td><code>{a[0]}</code></td><td>{e(a[1])}<span class="sub">feeds: {e(a[8])}</span></td><td class="num">{e(a[2])}</td><td class="rng">{e(a[3])}</td><td>{e(a[4])}<span class="sub">{e(a[5])}</span></td>'
        f'<td><span class="lbl lbl-{a[6].lower()}">{a[6]}</span></td><td>{e(a[7])}</td><td>{a[9]}</td><td>{e(a[10])}</td><td>{chip(*a[11])}</td></tr>'
        for a in assumptions)

    evidence = [
        ("2026-10-29", "Scheduled", "Q4 FY2026 earnings (consensus EPS $1.98)", "EV03 earnings release", "3", "Scheduled post-earnings reassessment - Opus 5.5, overnight batch, within 2 trading days", ("watch", "Scheduled")),
        ("2026-10-28", "Shared event", "FOMC decision", "SE02 rates", "1-2", "House rate deck revised once; WACC and every rate-linked driver recalculated by code", ("watch", "Scheduled")),
        ("Pending", "Shared event", "US v. Google remedy on the Safari default payment", "EV21 legal · shared with GOOGL", "4 on ruling",
         "One digest updates AAPL (Services revenue) and GOOGL (traffic-acquisition cost) with the same parameters", ("watch", "Watching")),
        ("2027-03-31", "Regulatory", "EU DMA App Store commission review", "EV21 regulatory (authored calendar)", "3", "Event reassessment of Services take rate", ("watch", "Scheduled")),
        ("2026Q3 call", "Transcript", "Management tone +0.20 vs analysts +0.00 - flagged 'candid'", "EV33 transcript · JEV Q16", "2", "Evidence log only; feeds C28", ("good", "Logged")),
        ("2026-10-05", "Consensus", "House EPS $8.50 vs consensus $9.58 (-11.3%)", "EV28 divergence", "1", "Below the >= 2x divergence rule; no action", ("good", "Logged")),
        ("Rolling", "Shared event", "Tariff actions on China assembly", "SE06 tariff · JEV Q10 exposure", "3", "Parameter set applied to every exposed hardware name", ("watch", "Watching")),
    ]
    erows = "".join(f'<tr><td>{d}</td><td>{e(c)}</td><td>{e(t)}</td><td>{e(s)}</td><td class="num">{m}</td><td>{e(a)}</td><td>{chip(*st)}</td></tr>'
                    for d, c, t, s, m, a, st in evidence)

    kpis = [
        ("Services growth", "+12%", "House 12% · break < 10%", "good"),
        ("iPhone growth", "+2%", "House +2% · break < -1%", "good"),
        ("Services share of revenue", "26%", f"{serv_ebit_share:.0%} of segment EBIT (est.)", "good"),
        ("GAAP operating margin", "33.2%", "TTM to 2026-06-30 · FY2025 32.0%", "good"),
        ("FCF margin", "23.7%", "FCF - SBC $85.9bn · SBC ~3% of revenue", "good"),
        ("Gross margin", "◌", "Extracted at build · break < 45%", "pend"),
        ("Greater China share", "~17-19%", "Growth extracted at build · break < -8%", "pend"),
        ("Capex intensity", "3.1%", "55% maintenance / 45% growth", "good"),
    ]
    ktiles = "".join(f'<div class="tile"><div class="tl">{e(k)}</div><div class="tv">{e(v)}</div><div class="ts">{e(s)}</div></div>' for k, v, s, _ in kpis)

    issues = [
        ("Equity bridge sign", "The DCF adds '+ net cash $55.0bn' to reach equity, but the balance sheet and inputs table report net debt of $57.7bn. "
         "The difference is about $113bn, roughly $7.5 a share on 15.0bn diluted shares (the SOTP lever row also adds net cash). Period/sign coherence check (AF-031) blocks the value until resolved."),
        ("Guidance label (D-372)", "'FY+1 guided revenue $465.0bn' and 'FY+1 guided EPS $8.5' are typed 'company guidance'. Apple does not issue annual revenue or EPS guidance; these are house estimates."),
        ("Model coherence", "Monte Carlo puts 7% of paths above spot while the authored scenarios put 30% of probability above spot. With PWEV and MC on shared drivers, this becomes a validation item to resolve, not a footnote."),
        ("Caption mismatch", "The scenario chart caption reads 'Five-scenario tree'; four scenarios are authored (the cross-check table says so)."),
        ("Missing rationale", "All five thesis-break triggers read 'rationale withheld pending re-authoring'. The foundation schema makes a rationale mandatory for every invalidation condition."),
        ("Stale description", "The company overview quotes 2020 revenue ($274.5bn) from the vendor description. C19 refreshes the overview from the 10-K Item 1 digest."),
    ]
    ihtml = "".join(f"<li><b>{e(t)}.</b> {e(d)}</li>" for t, d in issues)

    css = CSS
    page = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AAPL — Future Report Example</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Spectral:wght@400;600&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body class="annotated">
<div class="banner" role="note">
  <div><b>Example rendering — not published research.</b> Layout of the AAPL page under the analytical-foundation design. Figures are carried from the live page (run 6 Oct 2026, prices 5 Oct 2026). {PEND} marks a value the new pipeline produces that today's page does not have.</div>
  <label class="toggle"><input type="checkbox" id="annToggle" checked> Design annotations</label>
</div>
<header class="brandbar"><span class="mark">MCH ANALYSIS</span><span class="badge">EQUITY RESEARCH</span><span class="gen">General research — not personal financial advice</span></header>
<main class="wrap">

<section id="c01" class="hero">
  {ann("C01 · C46", "Changed", "Code; owner approves rating flips", "Nightly 02:00 SAST · price 1 trading day")}
  <div class="crumbs">Information Technology · Technology Hardware, Storage &amp; Peripherals · <b>Archetype AR05 Hardware + SM07 multi-segment</b></div>
  <h1>Apple Inc. <span class="tkr">AAPL</span></h1>
  <div class="herogrid">
    <div class="rating"><div class="rl">Rating</div><div class="rv sell">SELL</div><div class="rs">conviction medium · 70.7/100</div></div>
    <div class="fv">
      <div class="rl">Fair value</div>
      <div class="big">$225 <span class="neg">−32%</span></div>
      <div class="rs">Production blend (DCF 41 · PWEV 29 · MC 18 · peer 12). Archetype-blend value {PEND} (shadow, AF-055)</div>
    </div>
    <div class="spot"><div class="rl">Price</div><div class="big">$333</div><div class="rs">5 Oct 2026 · 52-week $243–$345 · fwd P/E 39.2x house / 34.8x consensus</div></div>
  </div>
  <p class="lede">Every primary and secondary anchor available today sits between <b>$192 and $228</b> — 32% to 42% below spot. The price pays a Services multiple on a hardware base growing low single digits; the multiple, not the franchise, carries 84% of Monte Carlo variance.</p>
  <div class="strip">
    <span>Next catalyst <b>29 Oct 2026</b> — Q4 FY26 earnings</span>
    <span>Primary thesis-break <b>Services growth &lt; 10%</b> for 2 prints — today +12%</span>
    <span>PWEV <b>$269</b> (−19%)</span>
  </div>
</section>

<section id="c03" class="badges">
  {ann("C03", "New", "Code", "Nightly · derived from dates and breach state")}
  <div class="badgerow">
    {chip("good", "Foundation current")}
    <span>Last full review <b>16 Aug 2026</b> (narrative by claude-fable-5, reviewed by Marinus) · 51 days of 100</span>
    <span>Next: post-earnings reassessment by <b>5 Nov 2026</b></span>
    <span>Thesis-breaks: <b>0 of 5 breached</b> · 2 awaiting data</span>
    {chip("flag", "2 validation flags")}
  </div>
</section>

<section id="c02" class="card">
  {ann("C02", "New", "Code diff + Sonnet 5.5 condensation", "Only after a reassessment · no expiry")}
  <h2>What changed</h2>
  <p class="meta">Foundation v1 — first structured build, compared with the legacy page of 6 Oct 2026</p>
  <ul class="changes">
    <li><b>Sum-of-the-parts becomes a primary anchor.</b> Services' estimated EBIT ($77.0bn, {serv_ebit_share:.0%} of segment EBIT) now exceeds iPhone's ($73.5bn), so SM07 applies. Effect on fair value: {PEND}. <span class="ev">Evidence: segment table (house estimates) · owner approval required because the EBIT split is estimated.</span></li>
    <li><b>Scenario PWEV and Monte Carlo move to the distribution layer.</b> They stop counting as independent anchors; their 30% vs 7% disagreement on upside is now a check to resolve. <span class="ev">Evidence: probability cross-checks · DEC-AF-03.</span></li>
    <li><b>Inputs relabelled.</b> FY+1 revenue $465.0bn and EPS $8.50 are house estimates, not company guidance. <span class="ev">Evidence: D-372 · Apple issues no annual guidance.</span></li>
  </ul>
</section>

<section id="c04" class="card two">
  <div>
    {ann("C04", "Existing", "Code", "Nightly")}
    <h2>Investment Committee summary</h2>
    <table class="kv">
      <tr><th>Rating</th><td>SELL · internal 5-tier SELL</td></tr>
      <tr><th>Classification · conviction</th><td>Mature cash generator · medium</td></tr>
      <tr><th>Evidence</th><td>8/8 load-bearing inputs sourced</td></tr>
      <tr><th>Fair value</th><td>$225 (−32%) production blend · archetype blend {PEND}</td></tr>
      <tr><th>12-month PWEV</th><td>$269 (−19%)</td></tr>
      <tr><th>Next catalyst</th><td>29 Oct 2026 — quarterly earnings</td></tr>
      <tr><th>Primary thesis-break</th><td>Services growth &lt; 10% for two consecutive prints</td></tr>
    </table>
  </div>
  <div>
    {ann("C06", "Changed", "Code (M21 reverse valuation)", "Nightly · price-driven")}
    <h2>What the market is pricing in</h2>
    <p>At $333 the market pays <b>34.8x</b> consensus forward EPS, against a house DCF terminal of 22.0x and a peer median of 26.5x. That implies roughly <b>4.9pp more revenue CAGR</b> than the house case.</p>
    <table class="kv">
      <tr><th></th><td><b>Consensus</b></td><td><b>House</b></td></tr>
      <tr><th>FY revenue</th><td>$528.0bn</td><td>$465.0bn (−11.9%)</td></tr>
      <tr><th>FY EPS</th><td>$9.58</td><td>$8.50 (−11.3%)</td></tr>
      <tr><th>Target</th><td>$328 (44 analysts)</td><td>$296</td></tr>
    </table>
  </div>
</section>

<section id="c07" class="card two">
  <div>
    {ann("C07", "Existing", "Opus 5.5 build · Sonnet 5.5 refresh", "On load-bearing change · max 184 days")}
    <h2>Investment thesis</h2>
    <ul class="thesis">
      <li><b>A multiple bet, not a franchise bet.</b> The P/E multiple explains 84% of Monte Carlo variance. <code>AAPL-SVC-X</code> <code>AAPL-TERM</code></li>
      <li><b>Services carries the premium.</b> Services must keep compounding at a double-digit pace for the multiple to hold. <code>AAPL-SVC-G</code></li>
      <li><b>Regulatory rents fund it.</b> The ~$20bn+ Google default payment and App Store take are under active antitrust and DMA attack. <code>AAPL-GOOG</code></li>
      <li><b>The AI upgrade cycle is optionality, not base case.</b> Apple Intelligence earns no direct revenue today. <code>AAPL-IPH-G</code></li>
    </ul>
    <p class="meta">Narrative as of 16 Aug 2026 · each bullet cites the assumptions it rests on</p>
  </div>
  <div>
    {ann("C08", "Existing", "Sonnet 5.5", "With thesis · negative evidence >= 3")}
    <h2>Anti-thesis — the real bear case</h2>
    <ul class="thesis">
      <li><b>No recession needed.</b> A final Google remedy removes a near-costless earnings stream in one ruling. → Structural Impairment (20%, $166)</li>
      <li><b>Commission erosion spreads.</b> DMA-style caps travel beyond the EU into App Store economics. → Services growth ~5%</li>
      <li><b>China weakens while AI under-delivers.</b> Huawei gains share and no measurable upgrade cycle appears. → iPhone units declining, ~10x multiple</li>
    </ul>
  </div>
</section>

<section id="c10" class="card">
  {ann("C10", "New", "Code applicability gate · JEV Q11/Q12 if borderline · owner approves", "Annual + on modifier change")}
  <h2>Method panel — which tools fit this business</h2>
  <p class="meta">Archetype <b>AR05 Hardware, networking &amp; components</b> (GICS rule) with modifier <b>SM07 multi-segment</b> (estimated EBIT split → borderline → JEV Q12 + owner approval). Weights pre-registered per DEC-AF-03: {PEND}</p>
  <div class="legend">{''.join(f'<span><span class="key" style="background:{c}"></span>{n}</span>' for n, c in ROLE.values())}</div>
  <div class="tw"><table class="methods"><thead><tr><th>ID</th><th>Method</th><th class="num">Value</th><th class="num">vs spot</th><th>Basis and notes</th></tr></thead><tbody>{''.join(mrows)}</tbody></table></div>
  <details><summary>Not applicable — with the economic reason (4 rows, 10 methods)</summary>
    <div class="tw"><table><thead><tr><th>Method</th><th>Code</th><th>Why it does not apply</th></tr></thead><tbody>{na_html}</tbody></table></div>
  </details>
  <details><summary>Available but not active — activated only by a modifier (3)</summary>
    <div class="tw"><table><thead><tr><th>Method</th><th>Activated by</th><th>Status for AAPL</th></tr></thead><tbody>{inact_html}</tbody></table></div>
  </details>
  <p class="foot">Not applicable means the business lacks the economic mechanism. A missing input shows as {PEND} or 'Not computed — input unavailable', never as N/A.</p>
</section>

<section id="c11" class="card">
  {ann("C11", "Changed", "Code", "Nightly + immediately on assumption change")}
  <h2>Valuation triangulation</h2>
  <p class="meta">Each method's value against spot; thin lines show the method's own range. Hover a mark for detail.</p>
  <div class="legend">{''.join(f'<span><span class="key" style="background:{c}"></span>{n}</span>' for n, c in ROLE.values())}</div>
  {valuation_chart()}
</section>

<section id="m16" class="card">
  {ann("M16 / C20", "New anchor", "Code", "On filing; multiple per assumption register")}
  <h2>Sum-of-the-parts — why the modifier fires</h2>
  <p>At the page's own segment multiples, Services is <b>{serv_share:.0%}</b> of segment value (${sotp_tot:,.0f}bn EV before net debt). The page's SOTP is <b>$228 a share</b> at a 28x Services multiple, from $184 at 19.6x to $271 at 36.4x.</p>
  {sotp_svg}
  <div class="tw"><table><thead><tr><th>Segment</th><th class="num">Revenue</th><th class="num">Mix</th><th class="num">Growth</th><th class="num">Op margin (est.)</th><th class="num">EBIT (est.)</th><th class="num">Multiple</th><th>Valued as</th></tr></thead><tbody>{seg_rows}</tbody></table></div>
</section>

<section id="c12" class="card">
  {ann("C12 · C13", "Existing", "Code targets nightly · Opus 5.5 reassesses probabilities", "Probabilities max 100 days")}
  <h2>Scenarios and distribution</h2>
  {scenario_chart()}
  <div class="tw"><table><thead><tr><th>Scenario</th><th class="num">Prob.</th><th>iPhone units</th><th class="num">Services growth</th><th class="num">Op margin</th><th class="num">Multiple</th><th class="num">Target</th><th class="num">vs spot</th></tr></thead><tbody>{scen_rows}
  <tr class="tot"><td>Probability-weighted (after 1.5% SBC dilution)</td><td class="num">100%</td><td></td><td></td><td></td><td></td><td class="num">$269</td><td class="num">−19%</td></tr></tbody></table></div>
  <h3>Monte Carlo — the outcome distribution</h3>
  {mc_chart()}
  <p class="flag">{chip("flag", "Coherence check")} Scenarios put 30% of probability above spot; the Monte Carlo puts 7% of paths there. Both now sit on the same drivers, so the gap must be resolved at the next reassessment rather than footnoted.</p>
</section>

<section id="c14" class="card">
  {ann("C14 · C37", "New / Changed", "Code", "Nightly")}
  <h2>Sensitivity — what moves the value</h2>
  <div class="two">
    <div>{heatmap()}</div>
    <div><h3>Load-bearing drivers, ranked by fair-value swing</h3>{tornado_chart()}</div>
  </div>
</section>

<section id="c15" class="card">
  {ann("C15", "Changed", "Code multiples · JEV Q13 scores peers · Sonnet 5.5 rationale", "Peer set semi-annual + corporate events")}
  <h2>Peers — split by segment under SM07</h2>
  <div class="tw"><table><thead><tr><th>Segment</th><th>Peer</th><th>Tier · cap</th><th class="num">Fwd P/E</th><th class="num">Growth</th><th class="num">Op margin</th><th>Why it is here <span class="sub">example rationale</span></th></tr></thead><tbody>
    <tr><td rowspan="3">Services (platform)</td><td>MSFT</td><td>direct · 100%</td><td class="num">30.0x</td><td class="num">16%</td><td class="num">45%</td><td>Platform and subscription economics at comparable scale</td></tr>
    <tr><td>GOOGL</td><td>segment · 50%</td><td class="num">28.0x</td><td class="num">14%</td><td class="num">32%</td><td>Search and app-store economics; counterparty to the default payment</td></tr>
    <tr><td>META</td><td>segment · 50%</td><td class="num">25.0x</td><td class="num">20%</td><td class="num">42%</td><td>Advertising-funded consumer platform</td></tr>
    <tr><td rowspan="2">Hardware (AR05)</td><td>DELL</td><td>broad · 25%</td><td class="num">15.0x</td><td class="num">5%</td><td class="num">9%</td><td>Device and PC hardware, far lower margin</td></tr>
    <tr><td colspan="6">{PEND} additional AR05 candidates scored by JEV Q13 within the D-527 size band</td></tr>
  </tbody></table></div>
  <p class="meta">Quality-weighted forward P/E 26.8x (simple median 26.5x) → $225.</p>
</section>

<section id="c21" class="card">
  {ann("C21", "New", "Code from filings · Haiku 4.5 extracts non-XBRL KPIs", "On filing · max 100 days")}
  <h2>Economic drivers and KPIs</h2>
  <div class="tiles">{ktiles}</div>
</section>

<section id="c09" class="card">
  {ann("C09 · C36", "Changed", "Code checks nightly · JEV Q15 for qualitative · Opus 5.5 reassessment", "Per row · default 100 days")}
  <h2>Assumption register and thesis-break monitor</h2>
  <p class="meta">Every material assumption with value or range, units, period, label, source, dependencies, last review and the condition that invalidates it. Ranges come from the scenario drivers on the page.</p>
  <div class="tw"><table class="reg"><thead><tr><th>ID</th><th>Assumption</th><th class="num">Value</th><th class="num">Range</th><th>Units · period</th><th>Label</th><th>Source</th><th>Reviewed</th><th>Invalidated when</th><th>Status</th></tr></thead><tbody>{arows}</tbody></table></div>
</section>

<section id="c31" class="card">
  {ann("C31", "New", "Code detectors · JEV Q01-Q10 · routes materiality >= 3", "Daily; intraday for materiality 4")}
  <h2>Evidence log and what happens next</h2>
  <div class="tw"><table><thead><tr><th>When</th><th>Class</th><th>Evidence</th><th>Trigger</th><th class="num">Materiality</th><th>What the system does</th><th>Status</th></tr></thead><tbody>{erows}</tbody></table></div>
  <p class="meta">Shared-event exposure tags: TARIFF (SE06), CHINA_EXPORT (SE07), AI_CAPEX (SE01, weak — Apple is not a supplier; JEV Q10 confirms or drops it). Last 365 days of news: 3,343 articles, average sentiment +0.12.</p>
</section>

<section id="c44" class="card audit">
  {ann("C44 · C43", "New", "Code", "Every run")}
  <h2>Methodology and provenance</h2>
  <table class="kv">
    <tr><th>Method set</th><td>Method matrix v1 (amendment pending) · AR05 + SM07 · N/A vocabulary v1</td></tr>
    <tr><th>Engine · decision layer</th><td>mch_stock_engine v2.0 · Research OS ros-1.20.0</td></tr>
    <tr><th>Data</th><td>Prices 5 Oct 2026 (Alpha Vantage) · balance sheet 30 Sep 2025 · segment model house estimates</td></tr>
    <tr><th>Foundation</th><td>v1 · built from the legacy page · reviewer: owner (Tier 1 — modifier needs approval)</td></tr>
  </table>
</section>

<aside class="card notes ann-only">
  <h2>Design notes — what the new validation gates find on today's page</h2>
  <ol>{ihtml}</ol>
  <p class="meta">These come straight from the live AAPL page. In the new pipeline the first three block or flag the affected value before publication; the last three are caught by schema and freshness rules.</p>
</aside>

<p class="disclaimer">Example rendering for internal design review. Not investment advice and not personal financial advice. Figures carried from MCH Analysis research dated 6 October 2026; placeholders mark values not yet produced.</p>
</main>
<script>
(function () {{
  var t = document.getElementById('annToggle');
  try {{ var s = localStorage.getItem('mch-ann'); if (s !== null) t.checked = s === '1'; }} catch (e) {{}}
  function apply() {{ document.body.classList.toggle('annotated', t.checked); try {{ localStorage.setItem('mch-ann', t.checked ? '1' : '0'); }} catch (e) {{}} }}
  t.addEventListener('change', apply); apply();
}})();
</script>
</body>
</html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT, len(page))


CSS = """
:root{--ink:#0E2A4E;--ink-soft:#45576F;--ink-faint:#546378;--paper:#EEF2F8;--paper-2:#E3EAF3;--rule:#CBD6E4;--blue:#1C5FA8;
--pos:#1F7A55;--neg:#A4382F;--bg:#FFFFFF;--surface:#FFFFFF;--text:#0E2A4E;--muted:#546378;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--negv:#e34948;--posv:#2a78d6;
--good:#0ca30c;--warn:#b07800;--crit:#d03b3b;--grid:#E3EAF3;
--mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--serif:'Spectral',Georgia,'Times New Roman',serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#E8EEF7;--ink-soft:#B9C6D8;--ink-faint:#9AA9BD;--paper:#16202D;--paper-2:#1E2A3A;
--rule:#2C3B50;--bg:#0F1722;--surface:#131D2A;--text:#E8EEF7;--muted:#9AA9BD;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--negv:#e66767;--posv:#3987e5;--grid:#22303F;--neg:#e66767;--pos:#4cc38a}}
:root[data-theme="dark"]{--ink:#E8EEF7;--ink-soft:#B9C6D8;--ink-faint:#9AA9BD;--paper:#16202D;--paper-2:#1E2A3A;--rule:#2C3B50;--bg:#0F1722;--surface:#131D2A;--text:#E8EEF7;--muted:#9AA9BD;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--negv:#e66767;--posv:#3987e5;--grid:#22303F}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--text);font:14px/1.55 var(--mono)}
.banner{position:sticky;top:0;z-index:5;display:flex;gap:16px;align-items:center;justify-content:space-between;padding:10px 16px;background:#FFF4D6;color:#4A3800;border-bottom:1px solid #E8D28C;font-size:12px}
@media (prefers-color-scheme: dark){.banner{background:#3A2F10;color:#F3E2B0;border-color:#5C4A1A}}
.toggle{white-space:nowrap;cursor:pointer}
.brandbar{display:flex;gap:12px;align-items:center;padding:12px 16px;background:#0E2A4E;color:#fff;font-size:12px;letter-spacing:.06em}
.brandbar .mark{font-weight:600}.brandbar .badge{border:1px solid #7FB1E6;padding:1px 6px;border-radius:3px}.brandbar .gen{margin-left:auto;opacity:.75}
.wrap{max-width:1080px;margin:0 auto;padding:16px}
.card,.hero,.badges{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:18px 20px;margin:0 0 14px}
h1{font:600 30px/1.2 var(--serif);margin:4px 0 10px}h2{font:600 20px/1.3 var(--serif);margin:0 0 6px}h3{font:600 15px/1.3 var(--serif);margin:16px 0 6px}
.tkr{font:500 16px var(--mono);color:var(--muted);margin-left:8px}
.crumbs,.meta,.foot,.sub,.muted{color:var(--muted)}.crumbs,.meta,.foot{font-size:12px}.sub{display:block;font-size:11px}
.herogrid{display:grid;grid-template-columns:1fr 1.6fr 1.3fr;gap:16px;margin:8px 0 12px}
.rl{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.rv{font:600 30px var(--serif)}.sell{color:var(--neg)}.big{font:600 30px var(--serif)}.big .neg{font-size:18px;color:var(--neg)}.rs{font-size:12px;color:var(--muted)}
.lede{font:17px/1.5 var(--serif);margin:8px 0}
.strip{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12px;border-top:1px solid var(--rule);padding-top:10px}
.badgerow{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;font-size:12px}
.chip{display:inline-flex;gap:4px;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;border:1px solid;white-space:nowrap}
.chip-good{color:#0a6e0a;border-color:#0ca30c;background:#ecf8ec}.chip-watch{color:#1c4f8f;border-color:#2a78d6;background:#eaf2fc}
.chip-pend{color:var(--muted);border-style:dashed;border-color:var(--muted);background:transparent}.chip-flag{color:#8a5a00;border-color:#eda100;background:#fff6e0}
.chip-bad{color:#a12a2a;border-color:#d03b3b;background:#fdeeee}
@media (prefers-color-scheme: dark){.chip-good{background:#123316;color:#9fe59f}.chip-watch{background:#13253d;color:#a9cbf5}.chip-flag{background:#3a2c08;color:#f3d48a}}
.pend{display:inline-block;padding:0 6px;border:1px dashed var(--muted);border-radius:4px;color:var(--muted);font-size:11px;white-space:nowrap}
.changes li,.thesis li{margin:0 0 8px}.ev{display:block;font-size:12px;color:var(--muted)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}thead th{font-weight:600;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.num{text-align:right;white-space:nowrap}.methods td:first-child,.reg td:first-child{white-space:nowrap}.reg .rng{white-space:normal;text-align:right}.kv th{width:42%;color:var(--muted);font-weight:500}
tr.grp td{background:var(--paper-2);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
tr.tot td{font-weight:600}
.note{color:var(--ink-soft);max-width:460px}
.tw{overflow-x:auto;margin:6px 0}
.key{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:baseline}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;margin:6px 0}
details{margin:8px 0;font-size:12px}summary{cursor:pointer;font-weight:600}
code{font:11px var(--mono);background:var(--paper-2);padding:1px 4px;border-radius:3px}
.chart{width:100%;height:auto;display:block;margin:6px 0}
.chart text{font:11px var(--mono);fill:var(--text);paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}.chart .tick{fill:var(--muted);font-size:10px}.chart .rowlab{font-size:11px}
.chart .muted{fill:var(--muted)}.chart .val{font-size:11px}.chart .reflabel{font-size:10px;fill:var(--text)}.chart .pendtxt{fill:var(--muted);font-style:italic}
.chart .grid{stroke:var(--grid);stroke-width:1}.chart .axis0{stroke:var(--muted);stroke-width:1}
.chart .ref{stroke:var(--text);stroke-width:1.5}.chart .ref2{stroke:var(--muted);stroke-width:1}
.chart .dot{stroke:var(--surface);stroke-width:2}.chart .mark:hover .dot{r:8}.chart .mark:hover path,.chart .mark:hover rect{filter:brightness(1.08)}
.heat td.hm{text-align:center;font-weight:500;border:2px solid var(--surface)}.heat td.base{outline:2px solid var(--text);outline-offset:-3px}
.heat caption{text-align:left;font-size:12px;color:var(--muted);margin-bottom:6px}.heat th{text-align:center}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.tile{border:1px solid var(--rule);border-radius:6px;padding:10px 12px}.tl{font-size:11px;color:var(--muted)}.tv{font:600 22px var(--serif)}.ts{font-size:11px;color:var(--muted)}
.lbl{font-size:10px;padding:1px 6px;border-radius:3px;border:1px solid var(--rule)}.lbl-fact{background:#eaf2fc;color:#1c4f8f}.lbl-estimate{background:#fff6e0;color:#7a5200}.lbl-judgement{background:#f3ecfb;color:#5b2d91}
@media (prefers-color-scheme: dark){.lbl-fact{background:#13253d;color:#a9cbf5}.lbl-estimate{background:#3a2c08;color:#f3d48a}.lbl-judgement{background:#2a1d3d;color:#cdb4f2}}
.reg td{font-size:11px}.reg .chip{white-space:normal;border-radius:8px}
.flag{font-size:12px}
.ann{display:none;gap:8px;flex-wrap:wrap;align-items:center;margin:-6px 0 10px;font-size:10px;color:var(--muted)}
.annotated .ann{display:flex}.ann span{border:1px solid var(--rule);border-radius:3px;padding:1px 6px}
.ann .cid{background:var(--ink);color:var(--surface);border-color:var(--ink);font-weight:600}
.ann .st-new,.ann .st-new{background:#ecf8ec;color:#0a6e0a;border-color:#0ca30c}.ann .st-changed{background:#fff6e0;color:#7a5200;border-color:#eda100}
.ann-only{display:none}.annotated .ann-only{display:block}
.notes{border-left:4px solid #eda100}.notes li{margin:0 0 8px;font-size:12px}
.audit .kv th{width:28%}
.disclaimer{font-size:11px;color:var(--muted);margin:20px 0}
@media (max-width:760px){.herogrid,.two{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(2,1fr)}.banner{flex-direction:column;align-items:flex-start}.brandbar .gen{display:none}h1{font-size:24px}}
"""

if __name__ == "__main__":
    build()
