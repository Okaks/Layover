"""
Layover - cross-border payment cost comparison.

Compares what a company pays on its current route against alternatives.
Nothing is assumed: every route is entered.

Settlement timings reference a primary interview with a serving treasury
analyst at a Nigerian fintech, August 2026.
"""

import altair as alt
import pandas as pd
import streamlit as st

import deck_export

st.set_page_config(page_title="Layover", page_icon="◆", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1300px;}
  h1, h2, h3 {letter-spacing: -0.015em;}
  .lede {color:#8FA3BF; font-size:0.95rem; line-height:1.6; max-width:72ch;}
  div[data-testid="column"] {display:flex;}
  div[data-testid="column"] > div {width:100%;}
  .card {border:1px solid #1E2836; border-radius:4px; padding:1.05rem 1.15rem;
         height:100%; display:flex; flex-direction:column;}
  .card-win {border-color:#E0A33E;}
  .cname {font-weight:600; font-size:1.02rem; margin-bottom:0.1rem; min-height:2.5em;}
  .csub {color:#8FA3BF; font-size:0.8rem; margin-bottom:0.9rem;}
  .big {font-size:1.8rem; font-weight:600; line-height:1.1;}
  .mid {font-size:1.25rem; font-weight:600; line-height:1.15;}
  .unit {color:#8FA3BF; font-size:0.77rem; text-transform:uppercase; letter-spacing:0.05em;}
  .hlabel {color:#8FA3BF; font-size:0.78rem; text-transform:uppercase;
           letter-spacing:0.05em; min-height:2.4em;}
  .rsub {color:#8FA3BF; font-size:0.8rem;}
  .down {color:#6ADFA0; font-size:0.82rem;}
  .up {color:#E88C8C; font-size:0.82rem;}
  .quote {border-left:2px solid #E0A33E; padding-left:0.9rem; color:#B8C4D4;
          font-size:0.92rem; line-height:1.65;}
</style>
""", unsafe_allow_html=True)

# symbol, indicative market rate per USD. The rate is only a starting point -
# it is editable, and a user should enter the actual rate on the day.
CURRENCIES = {
    "NGN ₦": ("₦", 1550.0),
    "KES KSh": ("KSh", 129.0),
    "GHS ₵": ("₵", 12.0),
    "ZAR R": ("R", 18.0),
    "EGP £E": ("£E", 48.0),
    "TZS TSh": ("TSh", 2600.0),
    "UGX USh": ("USh", 3700.0),
    "XOF CFA": ("CFA", 600.0),
    "EUR €": ("€", 0.92),
    "GBP £": ("£", 0.79),
}

# Route defaults. "premium" is how far above the market rate that route
# typically prices, as a multiplier - editable per route.
# "on_ramp"/"off_ramp" are the costs of converting into and out of the rail,
# as % of the payment. "prefund" is cash the route needs held in advance with
# a partner, in USD. All are editable placeholders.
DEFAULTS = [
    {"name": "Local domiciliary account", "fee_pct": 0.5, "premium": 1.019, "days": 2.0,
     "on_ramp": 0.0, "off_ramp": 0.0, "prefund": 0},
    {"name": "Offshore account, matched currency", "fee_pct": 0.3, "premium": 1.013, "days": 0.3,
     "on_ramp": 0.0, "off_ramp": 0.0, "prefund": 0},
    {"name": "Stablecoin settlement rail", "fee_pct": 0.5, "premium": 1.006, "days": 0.15,
     "on_ramp": 0.2, "off_ramp": 0.2, "prefund": 100_000},
]

BETTER, WORSE, TOTAL = "#2F95C2", "#CF6A5E", "#E0A33E"

st.title("What this transfer actually costs")
st.markdown(
    '<p class="lede">The fee is the visible part. The exchange rate you were given is usually the larger '
    'one, and it never appears on a statement. Enter each route you use or have been quoted, and compare '
    'them on total cost.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- inputs

st.sidebar.markdown("### The payment")
cur_label = st.sidebar.selectbox("Currency you pay from", list(CURRENCIES.keys()), index=0)
SYM, DEFAULT_RATE = CURRENCIES[cur_label]
CKEY = cur_label.split()[0]

amount = st.sidebar.number_input("Payment size (USD)", 1_000, 50_000_000, 260_000, 10_000,
                                 help="A single transfer, in the currency being bought.")
per_month = st.sidebar.number_input("Payments per month", 1, 500, 4)
step = 1.0 if DEFAULT_RATE >= 50 else 0.01
mkt_rate = st.sidebar.number_input(
    f"Market rate ({SYM} per USD)", 0.0, 1_000_000.0, DEFAULT_RATE, step,
    key=f"mkt_{CKEY}",
    help="The mid-market or official rate on the day. Every route's margin is measured against this. "
         "The figure shown is indicative - replace it with the actual rate.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### The routes")
st.sidebar.caption("Enter each route you use or have been quoted. The first is treated as your current one.")

routes = []
for i, d in enumerate(DEFAULTS):
    with st.sidebar.expander(d["name"], expanded=(i == 0)):
        name = st.text_input("Name", d["name"], key=f"n{i}")
        fee_pct = st.number_input("Fee (%)", 0.0, 10.0, d["fee_pct"], 0.05, key=f"f{i}")
        rate = st.number_input(f"Rate you get ({SYM} per USD)", 0.0, 1_000_000.0,
                               round(mkt_rate * d["premium"], 2), step, key=f"r{i}_{CKEY}")
        days = st.number_input("Days to land", 0.0, 30.0, d["days"], 0.05, key=f"d{i}")
        on_ramp = st.number_input("On-ramp cost (%)", 0.0, 10.0, d["on_ramp"], 0.05, key=f"on{i}",
                                  help="Cost of converting into the rail, if separate from the rate above.")
        off_ramp = st.number_input("Off-ramp cost (%)", 0.0, 10.0, d["off_ramp"], 0.05, key=f"off{i}",
                                   help="Cost of converting out of the rail at the receiving end.")
        prefund = st.number_input("Held in advance (USD)", 0, 100_000_000, d["prefund"], 10_000, key=f"p{i}",
                                  help="Cash this route needs parked with a partner before payments can go out.")
        active = st.checkbox("Include", value=True, key=f"a{i}")
    if active:
        routes.append({"name": name, "fee_pct": fee_pct, "rate": rate, "days": days,
                       "on_ramp": on_ramp, "off_ramp": off_ramp, "prefund": prefund})

st.sidebar.markdown("---")
st.sidebar.markdown("### The treasury")
opening = st.sidebar.number_input("Balance at start of month (USD)", 0, 1_000_000_000, 2_000_000, 50_000,
                                  help="Used for the closing position. Every route starts from the same balance.")
show_capital = st.sidebar.checkbox(
    "Price money in transit and held in advance", value=True,
    help="Cash in transit or parked with a partner is cash not working elsewhere. "
         "This prices it at your cost of capital.",
)
rate_pct = st.sidebar.slider("Cost of capital, annual (%)", 5, 40, 22) if show_capital else 0

st.sidebar.markdown("---")
st.sidebar.caption(
    "Nothing here is assumed - every route is entered. Settlement timings reference a primary interview "
    "with a serving treasury analyst at a Nigerian fintech, August 2026."
)

if not routes:
    st.warning("Include at least one route in the sidebar.")
    st.stop()

# ---------------------------------------------------------------- model

per_year = per_month * 12
annual_rate = rate_pct / 100 if show_capital else 0.0

for r in routes:
    r["fee"] = amount * r["fee_pct"] / 100
    r["spread_pct"] = ((r["rate"] - mkt_rate) / mkt_rate * 100) if mkt_rate else 0.0
    r["spread"] = amount * r["spread_pct"] / 100
    r["ramp_pct"] = r["on_ramp"] + r["off_ramp"]
    r["ramp"] = amount * r["ramp_pct"] / 100
    r["total"] = r["fee"] + r["spread"] + r["ramp"]
    # monthly components
    r["m_fee"] = r["fee"] * per_month
    r["m_fx"] = r["spread"] * per_month
    r["m_ramp"] = r["ramp"] * per_month
    r["in_transit"] = amount * per_month * r["days"] / 30
    r["m_transit"] = amount * per_month * r["days"] * annual_rate / 365
    r["m_prefund"] = r["prefund"] * annual_rate / 12
    r["m_cost"] = r["m_fee"] + r["m_fx"] + r["m_ramp"] + r["m_transit"] + r["m_prefund"]
    r["tied_up"] = r["in_transit"] + r["prefund"]
    r["closing"] = opening - amount * per_month - r["m_cost"]
    r["carry"] = (r["m_transit"] + r["m_prefund"]) * 12
    r["annual"] = r["m_cost"] * 12

current = routes[0]
best = min(routes, key=lambda r: r["annual"])
diff = current["annual"] - best["annual"]
diff_pct = 100 * diff / current["annual"] if current["annual"] else 0

# ---------------------------------------------------------------- headline

st.markdown("---")
head = [
    ("Cost of one transfer today", f"${current['total']:,.0f}",
     f"${current['fee']:,.0f} fee &middot; ${current['spread']:,.0f} exchange rate margin"
     + (f" &middot; ${current['ramp']:,.0f} on/off-ramp" if current["ramp"] else "")),
    ("Cheapest route entered", f"${best['total']:,.0f}", best["name"]),
    ("Difference over a year", f"${abs(diff):,.0f}",
     (f'<span class="down">&#9660; {abs(diff_pct):.0f}% lower</span>' if diff > 0
      else f'<span class="rsub">already the cheapest</span>')
     + f" &middot; {per_year} transfers"),
]
for col, (label, value, sub) in zip(st.columns(3), head):
    with col:
        st.markdown(
            f'<div class="card"><div class="hlabel">{label}</div>'
            f'<div class="big" style="margin:0.35rem 0 0.25rem;">{value}</div>'
            f'<div class="rsub">{sub}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("")
for col, r in zip(st.columns(len(routes)), routes):
    win = " card-win" if r is best and len(routes) > 1 else ""
    tag = "What you pay today" if r is current else "Alternative"
    ramp_line = (f'<div class="unit">On/off-ramp</div>'
                 f'<div class="mid">${r["ramp"]:,.0f}</div>'
                 f'<div class="rsub" style="margin-bottom:0.6rem;">{r["on_ramp"]:.2f}% in &middot; '
                 f'{r["off_ramp"]:.2f}% out</div>')
    carry_line = (f'<div class="unit">Cash tied up</div>'
                  f'<div class="mid">${r["tied_up"]:,.0f}</div>'
                  f'<div class="rsub" style="margin-bottom:0.6rem;">${r["in_transit"]:,.0f} in transit &middot; '
                  f'${r["prefund"]:,.0f} held in advance &middot; ${r["carry"]:,.0f} a year at {rate_pct}%</div>'
                  if show_capital else
                  f'<div class="unit">Cash tied up</div>'
                  f'<div class="mid">${r["tied_up"]:,.0f}</div>'
                  f'<div class="rsub" style="margin-bottom:0.6rem;">${r["in_transit"]:,.0f} in transit &middot; '
                  f'${r["prefund"]:,.0f} held in advance</div>')
    with col:
        st.markdown(
            f'<div class="card{win}">'
            f'<div class="cname">{r["name"]}</div>'
            f'<div class="csub">{tag}</div>'
            f'<div class="unit">Fee</div>'
            f'<div class="mid">${r["fee"]:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">{r["fee_pct"]:.2f}% per transfer</div>'
            f'<div class="unit">Exchange rate margin</div>'
            f'<div class="mid">${r["spread"]:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">'
            f'{SYM}{r["rate"]:,.0f} against {SYM}{mkt_rate:,.0f} &middot; {r["spread_pct"]:.2f}%</div>'
            f'{ramp_line}'
            f'{carry_line}'
            f'<div class="unit">Total per transfer</div>'
            f'<div class="big">${r["total"]:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">${r["annual"]:,.0f} across {per_year}</div>'
            f'<div class="unit">Time to land</div>'
            f'<div class="mid" style="margin-bottom:0.6rem;">{r["days"]:.2g} days</div>'
            f'<div class="unit">Closing position, month end</div>'
            f'<div class="mid">${r["closing"]:,.0f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
if current["spread"] > current["fee"]:
    st.markdown(
        f'<div class="card"><div><span style="font-weight:600;">The margin is the part that does not appear on a statement.</span> '
        f'A rate of {SYM}{current["rate"]:,.0f} against {SYM}{mkt_rate:,.0f} is a margin of '
        f'{current["spread_pct"]:.2f}%. On a payment of &#36;{amount:,.0f} that is '
        f'<span style="font-weight:600;">&#36;{current["spread"]:,.0f}</span>, against a fee of &#36;{current["fee"]:,.0f}.</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- bridge

alts = [r for r in routes if r is not current]
if alts:
    st.markdown("---")
    default_alt = next((r for r in alts if "stablecoin" in r["name"].lower()),
                       min(alts, key=lambda r: r["annual"]))
    pick = st.selectbox("Compare the current route against", [r["name"] for r in alts],
                        index=alts.index(default_alt))
    alt_r = next(r for r in alts if r["name"] == pick)

    gain = alt_r["closing"] - current["closing"]
    k1, k2, k3 = st.columns(3)
    for col, (label, value, sub) in zip((k1, k2, k3), [
        ("Closing position, before", f"${current['closing']:,.0f}", current["name"]),
        ("Closing position, after", f"${alt_r['closing']:,.0f}", alt_r["name"]),
        ("Change in a month", f"{'+' if gain >= 0 else '-'}${abs(gain):,.0f}",
         f"${abs(gain) * 12:,.0f} over a year"),
    ]):
        with col:
            st.markdown(
                f'<div class="card"><div class="hlabel">{label}</div>'
                f'<div class="big" style="margin:0.35rem 0 0.25rem;">{value}</div>'
                f'<div class="rsub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

    steps = [
        ("Fees", "m_fee"), ("Exchange rate margin", "m_fx"), ("On/off-ramp", "m_ramp"),
        ("Settlement time", "m_transit"), ("Held in advance", "m_prefund"),
    ]
    deltas = [(lbl, alt_r[key] - current[key]) for lbl, key in steps]
    if not show_capital:
        deltas = [d for d in deltas if d[0] not in ("Settlement time", "Held in advance")]
    deltas.sort(key=lambda d: abs(d[1]), reverse=True)

    rows, run = [], current["m_cost"]
    rows.append({"step": "Before", "start": 0.0, "end": run, "kind": "Route cost",
                 "label": f"${run:,.0f}", "delta": run})
    for lbl, dv in deltas:
        rows.append({"step": lbl, "start": run, "end": run + dv,
                     "kind": "Lowers cost" if dv < 0 else "Raises cost",
                     "label": ("$0" if round(dv) == 0 else f"{'+' if dv > 0 else '-'}${abs(dv):,.0f}"),
                     "delta": dv})
        run += dv
    rows.append({"step": "After", "start": 0.0, "end": run, "kind": "Route cost",
                 "label": f"${run:,.0f}", "delta": run})
    df = pd.DataFrame(rows)
    df["top"] = df[["start", "end"]].max(axis=1)
    order = list(df["step"])

    st.markdown("")
    st.markdown(f"**Monthly cost: \\${current['m_cost']:,.0f} before, \\${alt_r['m_cost']:,.0f} after**")
    color = alt.Color("kind:N", title=None,
                      scale=alt.Scale(domain=["Route cost", "Lowers cost", "Raises cost"],
                                      range=[TOTAL, BETTER, WORSE]),
                      legend=alt.Legend(orient="top", labelColor="#B8C4D4"))
    base = alt.Chart(df).encode(x=alt.X("step:N", sort=order, title=None,
                                        axis=alt.Axis(labelAngle=0, labelColor="#B8C4D4",
                                                      labelLimit=140, domainColor="#1E2836", ticks=False)))
    bars = base.mark_bar(size=46, cornerRadius=3).encode(
        y=alt.Y("start:Q", title=None,
                axis=alt.Axis(format="$,.0f", labelColor="#8FA3BF", gridColor="#1A2433", domain=False,
                              tickCount=5)),
        y2="end:Q", color=color,
        tooltip=[alt.Tooltip("step:N", title="Step"), alt.Tooltip("label:N", title="Amount")],
    )
    text = base.mark_text(dy=-9, color="#DCE3EC", fontSize=12, fontWeight=600).encode(
        y="top:Q", text="label:N")
    chart = (bars + text).properties(height=360).configure_view(stroke=None).configure(
        background="transparent")
    st.altair_chart(chart, width="stretch")

    with st.expander("See the bridge as a table"):
        st.dataframe(
            pd.DataFrame({"Step": df["step"], "Amount (USD)": df["label"]}),
            hide_index=True, width="stretch",
        )

# ---------------------------------------------------------------- beyond cost

st.markdown("---")
b1, b2 = st.columns([1, 1.1])
with b1:
    st.markdown("**Beyond the arithmetic**")
    st.markdown(
        "- **How the rate is set.** Negotiated per transaction, or published.\n"
        "- **When settlement happens.** Banking hours, or continuous.\n"
        "- **When verification happens.** Once at onboarding, or at payment time."
    )
with b2:
    st.markdown(
        '<div class="quote">The partners processing these payments mostly aren\'t local entities. They want '
        'the invoice, the company registration, the payer\'s details, the source of funds. And most of the '
        'time our people here don\'t have all of it.</div>',
        unsafe_allow_html=True,
    )
    st.caption("Treasury analyst, Nigerian fintech - condensed from a primary interview, August 2026")

# ---------------------------------------------------------------- export

st.markdown("---")
ex1, ex2 = st.columns([1, 2.2])
with ex1:
    ctx = {
        "amount": amount, "per_month": per_month, "per_year": per_year,
        "market": mkt_rate, "symbol": SYM, "routes": routes,
        "current": current, "best": best, "diff": diff, "diff_pct": diff_pct,
        "show_capital": show_capital, "rate_pct": rate_pct, "opening": opening,
        "alt": alt_r if alts else None,
    }
    try:
        deck_bytes = deck_export.build_deck(ctx)
        st.download_button(
            "Download this as a deck",
            data=deck_bytes,
            file_name="layover-comparison.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )
    except Exception as exc:
        st.button("Download this as a deck", disabled=True)
        st.caption(f"Deck export unavailable: {exc}")
with ex2:
    st.caption("Five slides built from the figures on this page, including the inputs used.")

st.markdown("")
with st.expander("How this is calculated"):
    st.markdown("""
**Exchange rate margin** is the gap between the rate a route gives you and the market rate that day,
as a percentage of the payment. A rate of 1,580 against 1,550 is 1.94%. On a large payment that is
usually several times the fee.

**Total per transfer** is fee plus margin plus any on/off-ramp cost.

**Cash tied up** is money in transit (payments per month times days to land) plus cash held in advance
with a partner. Where the capital option is on, both are priced at your cost of capital.

**Closing position** is the opening balance, less the month's payments, less the month's cost of the
route. Every route starts from the same balance and makes the same payments, so the difference between
two closing positions is the difference in what each route costs.

**The bridge** moves from the current route's monthly cost to the chosen alternative's, one effect at a
time, largest first.

**Every route is entered.** Nothing about any of them is assumed.

**Settlement timings** reference a primary interview with a serving treasury analyst at a Nigerian
fintech, August 2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a
matched-currency offshore account landing same day within hours.
""")
