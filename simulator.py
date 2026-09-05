"""
Layover - cross-border payment cost comparison.

Compares what a company pays on its current route against alternatives.
Nothing is assumed: every route is entered.

Settlement timings reference a primary interview with a serving treasury
analyst at a Nigerian fintech, August 2026.
"""

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

CURRENCIES = {
    "USD $": ("$", 1.0), "NGN ₦": ("₦", 1.0), "KES KSh": ("KSh", 1.0),
    "GHS ₵": ("₵", 1.0), "ZAR R": ("R", 1.0), "EUR €": ("€", 1.0), "GBP £": ("£", 1.0),
}

DEFAULTS = [
    {"name": "Bank transfer", "fee_pct": 0.5, "rate": 1580.0, "days": 2.0},
    {"name": "FX agent", "fee_pct": 0.0, "rate": 1570.0, "days": 1.0},
    {"name": "Stablecoin settlement rail", "fee_pct": 0.5, "rate": 1565.0, "days": 0.15},
]

st.title("What this transfer actually costs")
st.markdown(
    '<p class="lede">The fee is the visible part. The exchange rate you were given is usually the larger '
    'one, and it never appears on a statement. Enter each route you use or have been quoted, and compare '
    'them on total cost.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- inputs

st.sidebar.markdown("### The payment")
cur_label = st.sidebar.selectbox("Currency you pay from", list(CURRENCIES.keys()), index=1)
SYM = CURRENCIES[cur_label][0]

amount = st.sidebar.number_input("Payment size (USD)", 1_000, 50_000_000, 260_000, 10_000,
                                 help="A single transfer, in the currency being bought.")
per_month = st.sidebar.number_input("Payments per month", 1, 500, 4)
mkt_rate = st.sidebar.number_input(
    f"Market rate ({SYM} per USD)", 0.0, 1_000_000.0, 1550.0, 1.0,
    help="The mid-market or official rate on the day. Every route's margin is measured against this.",
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
                               d["rate"], 1.0, key=f"r{i}")
        days = st.number_input("Days to land", 0.0, 30.0, d["days"], 0.05, key=f"d{i}")
        active = st.checkbox("Include", value=True, key=f"a{i}")
    if active:
        routes.append({"name": name, "fee_pct": fee_pct, "rate": rate, "days": days})

st.sidebar.markdown("---")
show_capital = st.sidebar.checkbox(
    "Also price capital in transit", value=False,
    help="Only relevant if money in transit is capital you would otherwise deploy.",
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
daily = rate_pct / 100 / 365 if show_capital else 0.0

for r in routes:
    r["fee"] = amount * r["fee_pct"] / 100
    r["spread_pct"] = ((r["rate"] - mkt_rate) / mkt_rate * 100) if mkt_rate else 0.0
    r["spread"] = amount * r["spread_pct"] / 100
    r["carry"] = amount * per_month * (r["days"] / 30) * daily * 365 if show_capital else 0.0
    r["total"] = r["fee"] + r["spread"]
    r["annual"] = r["total"] * per_year + r["carry"]

current = routes[0]
best = min(routes, key=lambda r: r["annual"])
diff = current["annual"] - best["annual"]
diff_pct = 100 * diff / current["annual"] if current["annual"] else 0

# ---------------------------------------------------------------- headline

st.markdown("---")
head = [
    ("Cost of one transfer today", f"${current['total']:,.0f}",
     f"${current['fee']:,.0f} fee &middot; ${current['spread']:,.0f} exchange rate margin"),
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
    carry_line = (f'<div class="unit">Capital in transit</div>'
                  f'<div class="mid">${r["carry"]:,.0f} a year</div>'
                  f'<div class="rsub" style="margin-bottom:0.6rem;">at {rate_pct}%</div>'
                  if show_capital else "")
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
            f'{carry_line}'
            f'<div class="unit">Total per transfer</div>'
            f'<div class="big">${r["total"]:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">${r["annual"]:,.0f} across {per_year}</div>'
            f'<div class="unit">Time to land</div>'
            f'<div class="mid">{r["days"]:.2g} days</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
if current["spread"] > current["fee"]:
    st.markdown(
        f'<div class="card"><b>The margin is the part that does not appear on a statement.</b> '
        f'A rate of {SYM}{current["rate"]:,.0f} against {SYM}{mkt_rate:,.0f} is a margin of '
        f'{current["spread_pct"]:.2f}%. On a payment of ${amount:,.0f} that is '
        f'<b>${current["spread"]:,.0f}</b> — against a fee of ${current["fee"]:,.0f}.</div>',
        unsafe_allow_html=True,
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
        "show_capital": show_capital, "rate_pct": rate_pct,
    }
    st.download_button(
        "Download this as a deck",
        data=deck_export.build_deck(ctx),
        file_name="layover-comparison.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        type="primary",
    )
with ex2:
    st.caption("Four slides built from the figures on this page, including the inputs used.")

st.markdown("")
with st.expander("How this is calculated"):
    st.markdown("""
**Exchange rate margin** is the gap between the rate a route gives you and the market rate that day,
as a percentage of the payment. A rate of 1,580 against 1,550 is 1.94%. On a large payment that is
usually several times the fee.

**Total per transfer** is fee plus margin. Where the capital option is on, money in transit is priced at
your cost of capital — relevant only if that capital would otherwise be deployed.

**Every route is entered.** Nothing about any of them is assumed.

**Settlement timings** reference a primary interview with a serving treasury analyst at a Nigerian
fintech, August 2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a
matched-currency offshore account landing same day within hours.
""")
