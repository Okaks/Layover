"""
Layover - settlement route simulator.

Prices the working capital a company ties up because cross-border settlement
takes time: money in transit, and money held against the delay.

Route timings come from a primary interview with a serving treasury analyst at
a Nigerian fintech, August 2026.
"""

import streamlit as st

st.set_page_config(page_title="Layover", page_icon="◆", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1300px;}
  h1, h2, h3 {letter-spacing: -0.015em;}
  .lede {color:#8FA3BF; font-size:0.95rem; line-height:1.6; max-width:70ch;}
  .route {border:1px solid #1E2836; border-radius:4px; padding:1rem 1.1rem; height:100%;}
  .route-win {border-color:#E0A33E;}
  .rname {font-weight:600; font-size:1.02rem; margin-bottom:0.15rem;}
  .rsub {color:#8FA3BF; font-size:0.8rem; margin-bottom:0.9rem;}
  .big {font-size:1.9rem; font-weight:600; line-height:1.1;}
  .unit {color:#8FA3BF; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em;}
  .src {color:#6E7F96; font-size:0.82rem; line-height:1.55;}
  .quote {border-left:2px solid #E0A33E; padding-left:0.9rem; color:#B8C4D4;
          font-size:0.92rem; line-height:1.65;}
</style>
""", unsafe_allow_html=True)

ROUTES = {
    "local_dom": {
        "name": "Local domiciliary account",
        "sub": "Instruction to a local bank, settling cross-currency",
        "days_best": 1.0, "days_typical": 2.0, "days_worst": 3.0, "stall_rate": 0.22,
        "basis": ("Once it crosses currencies it is T+1 at best and can be T+2 or T+3. The bank may process "
                  "within the hour if pressed, or at end of day if not - and that depends on relationship, "
                  "not on anything the company controls."),
    },
    "offshore": {
        "name": "Offshore account, matched currency",
        "sub": "Paying from a USD account into a USD beneficiary",
        "days_best": 0.1, "days_typical": 0.3, "days_worst": 1.0, "stall_rate": 0.08,
        "basis": ("A US offshore account paying into the US lands same day, usually within hours. Requires "
                  "holding the currency in the right place before the invoice arrives."),
    },
    "stablecoin": {
        "name": "Stablecoin settlement rail",
        "sub": "Local currency in, stablecoin transport, local payout",
        "days_best": 0.05, "days_typical": 0.15, "days_worst": 0.5, "stall_rate": 0.06,
        "basis": ("Settles continuously rather than on banking hours. Verification sits with a regulated "
                  "counterparty holding the company's details from onboarding."),
    },
}

st.title("What does this payment actually cost you")
st.markdown(
    '<p class="lede">Not the fee. The days your money spends in transit, the capital you have to hold '
    'because of those days, and the share of payments that stall on paperwork. Built on what a serving '
    'treasury analyst described, not on list pricing.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- inputs

st.sidebar.markdown("### Your payment profile")
amount = st.sidebar.number_input(
    "Typical payment size (USD)", 1_000, 50_000_000, 250_000, 10_000,
    help="A single transaction, not a monthly or annual total.",
)
per_month = st.sidebar.slider("Payments per month", 1, 500, 12)

approach = st.sidebar.radio(
    "How you handle the delay",
    ["Hold capital against the delay", "Send when due and wait"],
    help="Whether you keep extra working capital available because settlement is slow, or simply "
         "send payments when they fall due and absorb the wait.",
)
holding = approach.startswith("Hold")

buffer_pct = 0
if holding:
    buffer_pct = st.sidebar.slider(
        "Buffer held against settlement delay (%)", 0, 100, 40,
        help="How much extra you keep on hand because money in transit isn't available.",
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### Local conditions")
rate = st.sidebar.slider("Cost of capital, annual (%)", 5, 40, 22,
                         help="What idle working capital costs you. Local money-market rates or your own "
                              "borrowing cost.")
stall_cost_days = st.sidebar.slider("Days lost when a payment stalls", 1, 30, 7,
                                    help="A payment held for documentation doesn't fail - it waits. "
                                         "This is how long before it clears.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Timings and stall rates come from a primary interview with a serving treasury analyst at a Nigerian "
    "fintech, August 2026. Cost of capital and buffer are yours to set - no assumption is hidden inside "
    "the model."
)

annual_volume = amount * per_month * 12
daily_rate = rate / 100 / 365


def evaluate(r):
    days = r["days_typical"]
    effective_days = days + r["stall_rate"] * stall_cost_days
    in_transit = amount * per_month * (effective_days / 30)
    buffer_held = amount * (buffer_pct / 100) * min(1.0, effective_days / 3.0) if holding else 0.0
    capital_tied = in_transit + buffer_held
    return {
        "days": days, "effective_days": effective_days,
        "in_transit": in_transit, "buffer_held": buffer_held,
        "capital_tied": capital_tied,
        "annual_cost": capital_tied * daily_rate * 365,
        "stalled": r["stall_rate"] * per_month * 12,
    }


results = {k: evaluate(v) for k, v in ROUTES.items()}
best = min(results, key=lambda k: results[k]["annual_cost"])
worst = max(results, key=lambda k: results[k]["annual_cost"])
saving = results[worst]["annual_cost"] - results[best]["annual_cost"]

# ---------------------------------------------------------------- headline

st.markdown("---")
h1, h2, h3 = st.columns(3)
h1.metric("Annual payment volume", f"${annual_volume:,.0f}")
h2.metric("Cost of the slowest route", f"${results[worst]['annual_cost']:,.0f}",
          help="Capital tied up in transit and in buffer, priced at your cost of capital.")
h3.metric("Difference against the fastest", f"${saving:,.0f}",
          delta=f"-{100*saving/max(results[worst]['annual_cost'],1):.0f}%", delta_color="inverse")

st.markdown("---")
cols = st.columns(3)
for col, (key, r) in zip(cols, ROUTES.items()):
    res = results[key]
    win = " route-win" if key == best else ""
    if holding:
        split = (f'<div class="rsub">${res["in_transit"]:,.0f} in transit &middot; '
                 f'${res["buffer_held"]:,.0f} held as buffer</div>')
    else:
        split = '<div class="rsub">all of it in transit</div>'
    with col:
        st.markdown(
            f'<div class="route{win}">'
            f'<div class="rname">{r["name"]}</div>'
            f'<div class="rsub">{r["sub"]}</div>'
            f'<div class="unit">Time to land</div>'
            f'<div class="big">{r["days_typical"]:.2g} <span style="font-size:1rem">days</span></div>'
            f'<div class="rsub">{r["days_best"]:.2g}-{r["days_worst"]:.2g} day range</div>'
            f'<div class="unit">Capital tied up</div>'
            f'<div class="big">${res["capital_tied"]:,.0f}</div>'
            f'{split}'
            f'<div class="unit">Annual cost of that capital</div>'
            f'<div class="big">${res["annual_cost"]:,.0f}</div>'
            f'<div class="rsub">{res["stalled"]:.0f} payments a year held for documentation</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
for key, r in ROUTES.items():
    with st.expander(f"Where the {r['name'].lower()} numbers come from"):
        st.markdown(f'<div class="src">{r["basis"]}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- compliance

st.markdown("---")
st.markdown("### The part that isn't about price")

ca, cb = st.columns([1.15, 1])
with ca:
    st.markdown(
        '<div class="quote">The partners processing these payments mostly aren\'t local entities. They want '
        'the invoice, the company registration, the payer\'s details, the source of funds. And most of the '
        'time our people here don\'t have all of it.</div>',
        unsafe_allow_html=True,
    )
    st.caption("Treasury analyst, Nigerian fintech - condensed from a primary interview, August 2026")

    st.markdown("**What a stalled payment actually is**")
    st.markdown(
        "- Not a pricing problem. The payment doesn't get more expensive - it doesn't happen.\n"
        "- The blocker is documentation: invoice, company registration, payer identity, source of funds.\n"
        "- Where that verification isn't already held, the request comes at payment time - when the money "
        "is meant to move.\n"
        "- Under a regulated counterparty, verification happens once at onboarding: due diligence, company "
        "registration, beneficial ownership.\n"
        "- After that, each payment runs against a company already verified, so compliance is a condition "
        "of access rather than a delay on every transfer."
    )

with cb:
    st.markdown("**Payments held for documentation, per year**")
    for key, r in ROUTES.items():
        st.markdown(
            f'<div style="padding:0.45rem 0; border-bottom:1px solid #1E2836;">{r["name"]}<br>'
            f'<span class="big" style="font-size:1.35rem;">{results[key]["stalled"]:.0f}</span> '
            f'<span class="rsub">of {per_month*12} payments</span></div>',
            unsafe_allow_html=True,
        )
    st.caption(
        f"At {stall_cost_days} days lost each, that's "
        f"{results['local_dom']['stalled']*stall_cost_days:.0f} days of delay a year on the slowest route "
        f"against {results['stablecoin']['stalled']*stall_cost_days:.0f} on the fastest."
    )

# ---------------------------------------------------------------- method

st.markdown("---")
with st.expander("How this is calculated"):
    st.markdown("""
**Capital tied up** is money in transit plus, where you hold one, the buffer kept against delay. Money in
transit is your monthly volume scaled by how long each payment takes. The buffer is what you keep on hand
because funds already sent aren't available yet - it scales with delay and reaches full size at three days,
on the reasoning that a company holding a buffer sizes it for the worst case it expects.

**Annual cost** prices that capital at the rate you set. It is an opportunity cost, not a fee: money
sitting in transit is money not working.

**Stall rate** is the share of payments held for documentation. The gap between routes isn't about how
strict compliance is - it's about whether the counterparty processing your payment understands local
documentation or treats it as an exception.

**Timings** come from a primary interview with a serving treasury analyst at a Nigerian fintech, August
2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a matched-currency offshore
account landing same day within hours. Stall rates are modelling assumptions rather than published figures.
""")
