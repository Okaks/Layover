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
  .ledger {display:flex; justify-content:space-between; font-size:0.9rem; color:#DCE3EC;
            padding:0.22rem 0;}
  .ledger em {font-style:normal; color:#8FA3BF; font-size:0.78rem; margin-left:0.3rem;}
  .ledger.zero {color:#5F6F85;}
  .ledger.total {border-top:1px solid #1E2836; margin-top:0.35rem; padding-top:0.55rem;
                 font-weight:600; font-size:1.05rem; margin-bottom:0.9rem;}
  .ledger.total span:last-child {font-size:1.6rem; line-height:1;}
  .trio {display:grid; grid-template-columns:repeat(3, 1fr); gap:0.6rem;
         border-top:1px solid #1E2836; padding-top:0.75rem;}
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
# as % of the payment. "prefund_days" is how many days of payments the route
# needs held in advance with a partner. All are editable placeholders.
DEFAULTS = [
    {"name": "Local domiciliary account", "fee_pct": 0.5, "premium": 1.019, "days": 2.0,
     "on_ramp": 0.0, "off_ramp": 0.0, "prefund_days": 0.0},
    {"name": "Offshore account, matched currency", "fee_pct": 0.3, "premium": 1.013, "days": 0.3,
     "on_ramp": 0.0, "off_ramp": 0.0, "prefund_days": 0.0},
    {"name": "Stablecoin settlement rail", "fee_pct": 0.5, "premium": 1.006, "days": 0.15,
     "on_ramp": 0.2, "off_ramp": 0.2, "prefund_days": 0.0},
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
        prefund_days = st.number_input(
            "Days of payments held in advance", 0.0, 60.0, d["prefund_days"], 0.5, key=f"p{i}",
            help="Days of payments this route needs parked with a partner before payments can go out, "
                 "for example the days it cannot top up plus a weekend buffer.")
        prefund = amount * per_month * prefund_days / 30
        st.caption(f"Scenario assumption, not a benchmark. {prefund_days:g} days = ${prefund:,.0f} held.")
        active = st.checkbox("Include", value=True, key=f"a{i}")
    if active:
        routes.append({"name": name, "fee_pct": fee_pct, "rate": rate, "days": days,
                       "on_ramp": on_ramp, "off_ramp": off_ramp, "prefund": prefund,
                       "prefund_days": prefund_days})

st.sidebar.markdown("---")
st.sidebar.markdown("### Idle cash")
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
def _line(label, value, sub=""):
    muted = " zero" if round(value) == 0 else ""
    return (f'<div class="ledger{muted}"><span>{label}{sub}</span>'
            f'<span>&#36;{value:,.0f}</span></div>')


for col, r in zip(st.columns(len(routes)), routes):
    win = " card-win" if r is best and len(routes) > 1 else ""
    tag = "What you pay today" if r is current else "Alternative"
    with col:
        st.markdown(
            f'<div class="card{win}">'
            f'<div class="cname">{r["name"]}</div>'
            f'<div class="csub">{tag}</div>'
            f'<div class="unit" style="margin-bottom:0.35rem;">Per transfer</div>'
            + _line("Fee", r["fee"], f' <em>{r["fee_pct"]:.2f}%</em>')
            + _line("Exchange rate margin", r["spread"], f' <em>{r["spread_pct"]:.2f}%</em>')
            + _line("On/off-ramp", r["ramp"], f' <em>{r["ramp_pct"]:.2f}%</em>')
            + f'<div class="ledger total"><span>Total delivered cost</span>'
              f'<span>&#36;{r["total"]:,.0f}</span></div>'
            f'<div class="trio">'
            f'<div><div class="unit">Per year</div><div class="mid">&#36;{r["annual"]:,.0f}</div></div>'
            f'<div><div class="unit">Time to land</div><div class="mid">{r["days"]:.2g} days</div></div>'
            f'<div><div class="unit">Cash tied up</div><div class="mid">&#36;{r["tied_up"]:,.0f}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("")
with st.expander("See the full breakdown"):
    rows_out = {
        "Fee per transfer": lambda r: f"${r['fee']:,.0f} ({r['fee_pct']:.2f}%)",
        "Rate you get": lambda r: f"{SYM}{r['rate']:,.0f} against {SYM}{mkt_rate:,.0f}",
        "Exchange rate margin per transfer": lambda r: f"${r['spread']:,.0f} ({r['spread_pct']:.2f}%)",
        "On/off-ramp per transfer": lambda r: f"${r['ramp']:,.0f} ({r['on_ramp']:.2f}% in, {r['off_ramp']:.2f}% out)",
        "Total delivered cost per transfer": lambda r: f"${r['total']:,.0f}",
        "Time to land": lambda r: f"{r['days']:.2g} days",
        "Cash in transit": lambda r: f"${r['in_transit']:,.0f}",
        "Cash held in advance": lambda r: f"${r['prefund']:,.0f} ({r['prefund_days']:g} days)",
        f"Cost of idle cash per year ({rate_pct}%)": lambda r: f"${r['carry']:,.0f}",
        "Total cost per year": lambda r: f"${r['annual']:,.0f}",
    }
    st.dataframe(pd.DataFrame({"": list(rows_out)} | {r["name"]: [f(r) for f in rows_out.values()]
                                                       for r in routes}),
                 hide_index=True, width="stretch", height=35 * (len(rows_out) + 1) + 3)

st.markdown("")
if current["spread"] > current["fee"]:
    st.markdown(
        f'<div class="card"><div><span style="font-weight:600;">The margin is the part that does not appear on a statement.</span> '
        f'A rate of {SYM}{current["rate"]:,.0f} against {SYM}{mkt_rate:,.0f} is a margin of '
        f'{current["spread_pct"]:.2f}%. On a payment of &#36;{amount:,.0f} that is '
        f'<span style="font-weight:600;">&#36;{current["spread"]:,.0f}</span>, against a fee of &#36;{current["fee"]:,.0f}.</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- cost by type

PART_KEYS = [("Exchange rate margin", "spread"), ("Fee", "fee"), ("On/off-ramp", "ramp")]
ROUTE_COLORS = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"]
route_names = [r["name"] for r in routes]
rows_c = []
for r in routes:
    for i, (part, key) in enumerate(PART_KEYS):
        rows_c.append({"part": part, "pi": i, "route": r["name"], "usd": r[key] * per_year})
    rows_c.append({"part": "Idle cash", "pi": 3, "route": r["name"], "usd": r["carry"]})
cdf = pd.DataFrame(rows_c)
cdf["label"] = cdf["usd"].map(lambda v: f"${v:,.0f}")
part_order = ["Exchange rate margin", "Fee", "On/off-ramp", "Idle cash"]
if not show_capital:
    cdf = cdf[cdf["part"] != "Idle cash"]
    part_order = part_order[:3]

st.markdown("---")
st.markdown("**Each cost, route by route, per year**")
xmax = max(cdf["usd"].max(), 1) * 1.18
panels = []
for part in part_order:
    pdf = cdf[cdf["part"] == part]
    order = list(pdf.sort_values("usd", ascending=False)["route"])
    y = alt.Y("route:N", sort=order, title=None,
              axis=alt.Axis(labelColor="#B8C4D4", labelLimit=240, labelFontSize=12,
                            domain=False, ticks=False, labelPadding=8, minExtent=200))
    bars = alt.Chart(pdf).mark_bar(height=18, cornerRadiusEnd=3).encode(
        y=y, x=alt.X("usd:Q", title=None, scale=alt.Scale(domain=[0, xmax]), axis=None),
        color=alt.Color("route:N", title=None, sort=route_names, legend=None,
                        scale=alt.Scale(domain=route_names, range=ROUTE_COLORS[:len(route_names)])),
        tooltip=[alt.Tooltip("part:N", title="Cost"), alt.Tooltip("route:N", title="Route"),
                 alt.Tooltip("label:N", title="Per year")],
    )
    labels = alt.Chart(pdf).mark_text(align="left", dx=6, color="#DCE3EC", fontSize=12,
                                      fontWeight=600).encode(y=y, x="usd:Q", text="label:N")
    panels.append((bars + labels).properties(
        height=34 * len(routes), width=700,
        title=alt.TitleParams(part, anchor="start", color="#DCE3EC", fontSize=13,
                              fontWeight=600, offset=6)))
small = alt.vconcat(*panels, spacing=22).configure_view(stroke=None).configure(
    background="transparent")
st.altair_chart(small, width="content")

# ---------------------------------------------------------------- beyond cost

st.markdown("---")
st.markdown("**Beyond the arithmetic**")
st.markdown(
    "- **How the rate is set.** Negotiated per transaction, or published.\n"
    "- **When settlement happens.** Banking hours, or continuous.\n"
    "- **When verification happens.** Once at onboarding, or at payment time."
)

# ---------------------------------------------------------------- export

st.markdown("---")
ex1, ex2 = st.columns([1, 2.2])
with ex1:
    ctx = {
        "amount": amount, "per_month": per_month, "per_year": per_year,
        "market": mkt_rate, "symbol": SYM, "routes": routes,
        "current": current, "best": best, "diff": diff, "diff_pct": diff_pct,
        "show_capital": show_capital, "rate_pct": rate_pct,
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
    st.caption("Four slides built from the figures on this page, including the inputs used.")

st.markdown("")
with st.expander("How this is calculated"):
    st.markdown("""
**Exchange rate margin** is the gap between the rate a route gives you and the market rate that day,
as a percentage of the payment. A rate of 1,580 against 1,550 is 1.94%. On a large payment that is
usually several times the fee.

**Total per transfer** is fee plus margin plus any on/off-ramp cost.

**Cash tied up** is money in transit (payments per month times days to land) plus cash held in advance
with a partner. Where the capital option is on, both are priced at your cost of capital.

**Every route is entered.** Nothing about any of them is assumed.

**Settlement timings** reference a primary interview with a serving treasury analyst at a Nigerian
fintech, August 2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a
matched-currency offshore account landing same day within hours.
""")
