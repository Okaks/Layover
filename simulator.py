"""
Layover - cross-border payment cost comparison.

Takes what a company pays on its current route and compares it against a
quoted alternative. Nothing is assumed: both sides are entered.

Settlement timings come from a primary interview with a serving treasury
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
  .cname {font-weight:600; font-size:1.02rem; margin-bottom:0.15rem; min-height:2.5em;}
  .csub {color:#8FA3BF; font-size:0.8rem; margin-bottom:0.9rem;}
  .big {font-size:1.85rem; font-weight:600; line-height:1.1;}
  .mid {font-size:1.3rem; font-weight:600; line-height:1.15;}
  .unit {color:#8FA3BF; font-size:0.77rem; text-transform:uppercase; letter-spacing:0.05em;}
  .hlabel {color:#8FA3BF; font-size:0.78rem; text-transform:uppercase;
           letter-spacing:0.05em; min-height:2.4em;}
  .rsub {color:#8FA3BF; font-size:0.8rem;}
  .down {color:#6ADFA0; font-size:0.82rem;}
  .up {color:#E88C8C; font-size:0.82rem;}
  .src {color:#6E7F96; font-size:0.82rem; line-height:1.55;}
  .quote {border-left:2px solid #E0A33E; padding-left:0.9rem; color:#B8C4D4;
          font-size:0.92rem; line-height:1.65;}
</style>
""", unsafe_allow_html=True)

st.title("What this transfer actually costs")
st.markdown(
    '<p class="lede">The fee is the visible part. The exchange rate you were given is usually the larger '
    'one, and it never appears on a statement. Enter what you pay today, enter what is being offered, '
    'and compare the two.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- inputs

st.sidebar.markdown("### The payment")
amount = st.sidebar.number_input("Payment size (USD)", 1_000, 50_000_000, 260_000, 10_000,
                                 help="A single transfer.")
per_month = st.sidebar.number_input("Payments per month", 1, 500, 4)

st.sidebar.markdown("---")
st.sidebar.markdown("### What you pay today")
cur_name = st.sidebar.text_input("Route or provider", "Bank transfer")
cur_fee_type = st.sidebar.radio("Fee is charged as", ["Flat amount", "Percentage"], horizontal=True)
if cur_fee_type == "Flat amount":
    cur_fee = st.sidebar.number_input("Fee per transfer (USD)", 0.0, 100_000.0, 50.0, 5.0)
else:
    cur_fee = amount * st.sidebar.number_input("Fee (%)", 0.0, 10.0, 0.5, 0.05) / 100

st.sidebar.caption("The rate you were given, and the market rate that day. Any currency, as long as both "
                   "are the same one.")
c1, c2 = st.sidebar.columns(2)
cur_rate = c1.number_input("Rate you got", 0.0, 100_000.0, 1580.0, 1.0)
mkt_rate = c2.number_input("Market rate", 0.0, 100_000.0, 1550.0, 1.0)
cur_days = st.sidebar.number_input("Days to land", 0.0, 30.0, 2.0, 0.25)

st.sidebar.markdown("---")
st.sidebar.markdown("### What is being offered")
alt_name = st.sidebar.text_input("Route or provider ", "Stablecoin settlement rail")
alt_fee_type = st.sidebar.radio("Fee charged as", ["Percentage", "Flat amount"], horizontal=True)
if alt_fee_type == "Flat amount":
    alt_fee = st.sidebar.number_input("Fee per transfer (USD) ", 0.0, 100_000.0, 100.0, 5.0)
else:
    alt_fee = amount * st.sidebar.number_input("Fee (%) ", 0.0, 10.0, 0.5, 0.05) / 100

alt_spread_pct = st.sidebar.number_input(
    "Combined spread across conversions (%)", 0.0, 10.0, 1.0, 0.05,
    help="Local currency to stablecoin, then stablecoin to the destination currency. Enter the combined "
         "figure, or your quoted rate for this client.",
)
alt_days = st.sidebar.number_input("Days to land ", 0.0, 30.0, 0.15, 0.05)

st.sidebar.markdown("---")
show_capital = st.sidebar.checkbox(
    "Also price capital in transit", value=False,
    help="Only relevant if money in transit is capital you would otherwise deploy. Many companies simply "
         "plan around the delay and carry no such cost.",
)
rate_pct = 0
if show_capital:
    rate_pct = st.sidebar.slider("Cost of capital, annual (%)", 5, 40, 22)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Nothing here is assumed. Both sides are entered - what you pay today, and what is being offered. "
    "Settlement timings reference a primary interview with a serving treasury analyst at a Nigerian "
    "fintech, August 2026."
)

# ---------------------------------------------------------------- model

cur_spread_pct = ((cur_rate - mkt_rate) / mkt_rate * 100) if mkt_rate else 0.0
cur_spread = amount * cur_spread_pct / 100
alt_spread = amount * alt_spread_pct / 100

daily = rate_pct / 100 / 365 if show_capital else 0.0
cur_carry = amount * per_month * (cur_days / 30) * daily * 365 if show_capital else 0.0
alt_carry = amount * per_month * (alt_days / 30) * daily * 365 if show_capital else 0.0

cur_total = cur_fee + cur_spread
alt_total = alt_fee + alt_spread
per_year = per_month * 12
cur_annual = cur_total * per_year + cur_carry
alt_annual = alt_total * per_year + alt_carry
diff = cur_annual - alt_annual
diff_pct = 100 * diff / cur_annual if cur_annual else 0
cheaper = diff > 0

# ---------------------------------------------------------------- headline

st.markdown("---")
head = [
    ("Cost of one transfer today", f"${cur_total:,.0f}",
     f"${cur_fee:,.0f} fee &middot; ${cur_spread:,.0f} exchange rate margin"),
    (f"The same transfer, offered", f"${alt_total:,.0f}",
     f"${alt_fee:,.0f} fee &middot; ${alt_spread:,.0f} spread"),
    ("Difference over a year", f"${abs(diff):,.0f}",
     (f'<span class="down">&#9660; {abs(diff_pct):.0f}% lower</span>' if cheaper
      else f'<span class="up">&#9650; {abs(diff_pct):.0f}% higher</span>')
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
routes = [
    (cur_name, "What you pay today", cur_fee, cur_spread, cur_spread_pct, cur_days, cur_total,
     cur_annual, cur_carry, "Negotiated per transaction", False),
    (alt_name, "What is being offered", alt_fee, alt_spread, alt_spread_pct, alt_days, alt_total,
     alt_annual, alt_carry, "Published pricing", cheaper),
]
for col, (name, sub, fee, spread, spct, days, total, annual, carry, pricing, win) in zip(
        st.columns(2), routes):
    with col:
        carry_line = (f'<div class="unit">Capital in transit</div>'
                      f'<div class="mid">${carry:,.0f} a year</div>'
                      f'<div class="rsub" style="margin-bottom:0.6rem;">at {rate_pct}% cost of capital</div>'
                      if show_capital else "")
        st.markdown(
            f'<div class="card{" card-win" if win else ""}">'
            f'<div class="cname">{name}</div>'
            f'<div class="csub">{sub}</div>'
            f'<div class="unit">Fee</div>'
            f'<div class="mid">${fee:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">per transfer</div>'
            f'<div class="unit">Exchange rate margin</div>'
            f'<div class="mid">${spread:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">{spct:.2f}% of the payment</div>'
            f'{carry_line}'
            f'<div class="unit">Total per transfer</div>'
            f'<div class="big">${total:,.0f}</div>'
            f'<div class="rsub" style="margin-bottom:0.6rem;">${annual:,.0f} across {per_year} transfers</div>'
            f'<div class="unit">Time to land</div>'
            f'<div class="mid">{days:.2g} days</div>'
            f'<div class="rsub">how the rate is set: {pricing.lower()}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
if cur_spread_pct > 0:
    st.markdown(
        f'<div class="card"><b>The margin is the part that does not appear on a statement.</b> '
        f'A rate of {cur_rate:,.0f} against a market rate of {mkt_rate:,.0f} is a margin of '
        f'{cur_spread_pct:.2f}%. On a payment of ${amount:,.0f} that is <b>${cur_spread:,.0f}</b> — '
        f'against a fee of ${cur_fee:,.0f}. Most finance teams know the fee to the naira and have never '
        f'seen the margin written down.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- beyond cost

st.markdown("---")
st.markdown("### Cost is one line of the comparison")

b1, b2 = st.columns([1.15, 1])
with b1:
    st.markdown(
        "Not every provider competes on price, and a company with a strong banking relationship may "
        "already have a good rate. Three things separate routes regardless of what the arithmetic above "
        "shows.\n\n"
        "**How the rate is set.** A negotiated rate moves with the relationship and the day. Published "
        "pricing is the same on a Tuesday in March as it is at quarter end.\n\n"
        "**When settlement happens.** A route that clears on banking hours behaves differently at a "
        "weekend or a public holiday from one that settles continuously.\n\n"
        "**When verification happens.** Held once at onboarding, or requested at payment time."
    )
with b2:
    st.markdown(
        '<div class="quote">The partners processing these payments mostly aren\'t local entities. They want '
        'the invoice, the company registration, the payer\'s details, the source of funds. And most of the '
        'time our people here don\'t have all of it.</div>',
        unsafe_allow_html=True,
    )
    st.caption("Treasury analyst, Nigerian fintech - condensed from a primary interview, August 2026")
    st.markdown(
        "- A held payment doesn't get more expensive. It doesn't happen.\n"
        "- Under a regulated counterparty, verification happens once at onboarding.\n"
        "- Each payment then runs against a company already verified."
    )

# ---------------------------------------------------------------- export

st.markdown("---")
ex1, ex2 = st.columns([1, 2.2])
with ex1:
    ctx = {
        "amount": amount, "per_month": per_month, "per_year": per_year,
        "current": {"name": cur_name, "fee": cur_fee, "spread": cur_spread,
                    "spread_pct": cur_spread_pct, "days": cur_days, "total": cur_total,
                    "annual": cur_annual, "carry": cur_carry, "rate": cur_rate, "market": mkt_rate},
        "offered": {"name": alt_name, "fee": alt_fee, "spread": alt_spread,
                    "spread_pct": alt_spread_pct, "days": alt_days, "total": alt_total,
                    "annual": alt_annual, "carry": alt_carry},
        "diff": diff, "diff_pct": diff_pct, "cheaper": cheaper,
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
    st.caption("Four slides built from the figures on this page, including the inputs used so the "
               "numbers can be checked.")

st.markdown("")
with st.expander("How this is calculated"):
    st.markdown("""
**Exchange rate margin** is the gap between the rate you were given and the market rate that day,
expressed as a percentage of the payment. A rate of 1,580 against a market rate of 1,550 is a margin of
1.94%. On a large payment that figure is usually several times the fee.

**Total per transfer** is the fee plus that margin. Where the capital option is switched on, the cost of
money in transit is added on top — relevant only if that capital would otherwise be deployed. Many
companies plan around the delay instead and carry no such cost.

**Both sides are entered.** Nothing about either route is assumed. What you pay today comes from your own
records; what is being offered comes from published pricing or a quoted rate.

**Settlement timings** reference a primary interview with a serving treasury analyst at a Nigerian
fintech, August 2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a
matched-currency offshore account landing same day within hours.
""")
