"""
Value Date - settlement route simulator.

Prices the working capital a company ties up because cross-border settlement
takes time - either waiting for money in transit, or releasing it early to be
sure a supplier is paid on time.

Route timings come from a primary interview with a serving treasury analyst at
a Nigerian fintech, August 2026. Every figure on the page is editable.
"""

import streamlit as st

st.set_page_config(page_title="Value Date", page_icon="◆", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1320px;}
  h1, h2, h3 {letter-spacing: -0.015em;}
  .lede {color:#8FA3BF; font-size:0.95rem; line-height:1.6; max-width:72ch;}
  .route {border:1px solid #1E2836; border-radius:4px; padding:1rem 1.1rem; height:100%;}
  .route-win {border-color:#E0A33E;}
  .rname {font-weight:600; font-size:1.02rem; margin-bottom:0.15rem;}
  .rsub {color:#8FA3BF; font-size:0.8rem; margin-bottom:0.9rem;}
  .big {font-size:1.75rem; font-weight:600; line-height:1.15;}
  .unit {color:#8FA3BF; font-size:0.76rem; text-transform:uppercase; letter-spacing:0.05em;}
  .src {color:#6E7F96; font-size:0.82rem; line-height:1.55;}
  .quote {border-left:2px solid #E0A33E; padding-left:0.9rem; color:#B8C4D4;
          font-size:0.92rem; line-height:1.65;}
</style>
""", unsafe_allow_html=True)

ROUTES = {
    "local_dom": {
        "name": "Local domiciliary account",
        "sub": "Instruction to a local bank, settling cross-currency",
        "days": 2.0, "hold": 22,
        "basis": ("Once it crosses currencies it is T+1 at best and can be T+2 or T+3. The bank may process "
                  "within the hour if pressed, or at end of day if not - and that depends on relationship, "
                  "not on anything the company controls."),
    },
    "offshore": {
        "name": "Offshore account, matched currency",
        "sub": "Paying from a USD account into a USD beneficiary",
        "days": 0.3, "hold": 8,
        "basis": ("A US offshore account paying into the US lands same day, usually within hours. Requires "
                  "holding the currency in the right place before the invoice arrives."),
    },
    "stablecoin": {
        "name": "Stablecoin settlement rail",
        "sub": "Local currency in, stablecoin transport, local payout",
        "days": 0.15, "hold": 6,
        "basis": ("Settles continuously rather than on banking hours. Verification sits with a regulated "
                  "counterparty holding the company's details from onboarding."),
    },
}

st.title("What settlement time costs you")
st.markdown(
    '<p class="lede">Cross-border settlement takes days, and those days cost money whether you wait for '
    'them or plan around them. Set the figures below to your own and see what your current route ties up.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- sidebar

st.sidebar.markdown("### Your payments")
st.sidebar.caption("Set these to your own figures. Every number on the page is built from what you enter.")

amount = st.sidebar.number_input(
    "Typical size of one payment (USD)", 1_000, 50_000_000, 250_000, 10_000,
    help="A single transaction, not a monthly or annual total.",
)
per_month = st.sidebar.slider("Payments per month", 1, 500, 12)
rate = st.sidebar.slider("Cost of capital, annual (%)", 5, 40, 22)

st.sidebar.markdown("---")
st.sidebar.markdown("### How you handle the delay")
approach = st.sidebar.radio(
    "",
    ["Send when due and wait", "Release early so it arrives on time"],
    label_visibility="collapsed",
)
lead_days = 0.0
if approach.startswith("Release"):
    lead_days = st.sidebar.slider("Days you release ahead of the due date", 0.5, 21.0, 5.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.markdown("### Route timings")
st.sidebar.caption("Days to land, and the share of payments held for documentation. Change these to match "
                   "what you actually see.")

routes = {k: dict(v) for k, v in ROUTES.items()}
for k in routes:
    st.sidebar.markdown(f"**{routes[k]['name']}**")
    c1, c2 = st.sidebar.columns(2)
    routes[k]["days"] = c1.number_input("days", 0.0, 30.0, float(ROUTES[k]["days"]), 0.05,
                                        key=f"d_{k}", label_visibility="visible")
    routes[k]["hold"] = c2.number_input("held %", 0, 60, ROUTES[k]["hold"], 1,
                                        key=f"h_{k}", label_visibility="visible")

st.sidebar.markdown("---")
stall_cost_days = st.sidebar.slider(
    "Extra days when a payment is held", 1, 30, 7,
    help="A payment stopped for documentation isn't lost, it waits. This is how long before it clears.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Route timings come from a primary interview with a serving treasury analyst at a Nigerian fintech, "
    "August 2026. Hold rates are modelling assumptions. Everything here is editable."
)

daily_rate = rate / 100 / 365
annual_volume = amount * per_month * 12


def evaluate(r):
    transit = r["days"] + (r["hold"] / 100) * stall_cost_days
    committed = max(transit, lead_days) if lead_days else transit
    early = max(0.0, committed - transit)
    cap_transit = amount * per_month * (transit / 30)
    cap_early = amount * per_month * (early / 30)
    return {
        "transit": transit, "early": early, "committed": committed,
        "cap_transit": cap_transit, "cap_early": cap_early,
        "capital": cap_transit + cap_early,
        "cost_transit": cap_transit * daily_rate * 365,
        "cost_early": cap_early * daily_rate * 365,
        "annual_cost": (cap_transit + cap_early) * daily_rate * 365,
        "held_per_year": (r["hold"] / 100) * per_month * 12,
    }


res = {k: evaluate(v) for k, v in routes.items()}
cheapest = min(res, key=lambda k: res[k]["annual_cost"])
dearest = max(res, key=lambda k: res[k]["annual_cost"])
saving = res[dearest]["annual_cost"] - res[cheapest]["annual_cost"]
planning = lead_days > 0

# ---------------------------------------------------------------- headline

st.markdown("---")
h1, h2, h3 = st.columns(3)
h1.metric("Annual payment volume", f"${annual_volume:,.0f}")
h2.metric("Capital tied up, slowest route", f"${res[dearest]['capital']:,.0f}")
h3.metric("Annual cost of that capital", f"${res[dearest]['annual_cost']:,.0f}",
          delta=f"${saving:,.0f} lower on the fastest route", delta_color="inverse")

st.markdown("---")
cols = st.columns(3)
for col, (key, r) in zip(cols, routes.items()):
    e = res[key]
    win = " route-win" if key == cheapest else ""
    if planning:
        detail = (
            f'<div class="unit">In transit</div>'
            f'<div class="big" style="font-size:1.35rem;">${e["cap_transit"]:,.0f}</div>'
            f'<div class="rsub">${e["cost_transit"]:,.0f} a year &middot; {e["transit"]:.1f} days moving</div>'
            f'<div class="unit">Released early</div>'
            f'<div class="big" style="font-size:1.35rem;">${e["cap_early"]:,.0f}</div>'
            f'<div class="rsub">${e["cost_early"]:,.0f} a year &middot; {e["early"]:.1f} days ahead of need</div>'
        )
    else:
        detail = (
            f'<div class="unit">Capital in transit</div>'
            f'<div class="big" style="font-size:1.35rem;">${e["cap_transit"]:,.0f}</div>'
            f'<div class="rsub">{e["transit"]:.1f} days moving</div>'
        )
    with col:
        st.markdown(
            f'<div class="route{win}">'
            f'<div class="rname">{r["name"]}</div>'
            f'<div class="rsub">{r["sub"]}</div>'
            f'<div class="unit">Settles in</div>'
            f'<div class="big">{r["days"]:.2g} <span style="font-size:0.95rem">days</span></div>'
            f'<div class="rsub">{e["transit"]:.1f} days once documentation holds are counted</div>'
            f'{detail}'
            f'<div class="unit">Annual cost</div>'
            f'<div class="big">${e["annual_cost"]:,.0f}</div>'
            f'<div class="rsub">{e["held_per_year"]:.0f} of {per_month*12} payments held for documents</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
c1, c2, c3 = st.columns(3)
for col, (key, r) in zip([c1, c2, c3], routes.items()):
    with col:
        with st.expander(f"Where the {r['name'].lower()} timing comes from"):
            st.markdown(f'<div class="src">{r["basis"]}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- planning

if planning:
    st.markdown("---")
    st.markdown("### Waiting and planning are both costs")
    cur = res[dearest]
    p1, p2 = st.columns([1.15, 1])
    with p1:
        st.markdown(
            f"Releasing **{lead_days:.1f} days** ahead means the money leaves the business before it is "
            f"owed. On the slowest route settlement genuinely takes **{cur['transit']:.1f} days**, so "
            f"**{cur['early']:.1f} days** of that is cover against a route you cannot predict.\\n\\n"
            f"Both cost the same rate. In transit runs to **${cur['cost_transit']:,.0f}** a year, cover to "
            f"**${cur['cost_early']:,.0f}**. The second only exists because the first is unreliable - a "
            f"route that lands when it says it will needs far less of it."
        )
    with p2:
        st.markdown("**Cover needed per route**")
        for key, r in routes.items():
            e = res[key]
            st.markdown(
                f'<div style="padding:0.45rem 0; border-bottom:1px solid #1E2836;"><b>{r["name"]}</b><br>'
                f'<span class="rsub">{e["transit"]:.1f}d moving &middot; {e["early"]:.1f}d cover &middot; '
                f'${e["annual_cost"]:,.0f}/yr</span></div>',
                unsafe_allow_html=True,
            )

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
    for key, r in routes.items():
        st.markdown(
            f'<div style="padding:0.45rem 0; border-bottom:1px solid #1E2836;">{r["name"]}<br>'
            f'<span class="big" style="font-size:1.3rem;">{res[key]["held_per_year"]:.0f}</span> '
            f'<span class="rsub">of {per_month*12} &middot; at {r["hold"]}%</span></div>',
            unsafe_allow_html=True,
        )
    st.caption(
        f"At {stall_cost_days} days added each, that is "
        f"{res['local_dom']['held_per_year']*stall_cost_days:.0f} days of delay a year on the slowest route "
        f"against {res['stablecoin']['held_per_year']*stall_cost_days:.0f} on the fastest."
    )

# ---------------------------------------------------------------- method

st.markdown("---")
with st.expander("How this is calculated"):
    st.markdown("""
    expected settlement = route days + (hold rate x extra days when held)
    capital in transit  = payment size x payments per month x (settlement days / 30)
    capital released early = payment size x payments per month x (days ahead of settlement / 30)
    annual cost         = capital tied up x your cost of capital

Capital tied up is an opportunity cost rather than a fee. It never appears on an invoice, which is why it
usually goes unpriced.

Route timings come from a primary interview with a serving treasury analyst at a Nigerian fintech, August
2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a matched-currency
offshore account landing same day within hours.

The documentation hold rates - 22% on a local domiciliary account, 8% offshore, 6% on a stablecoin rail -
are modelling assumptions rather than published figures. Change them in the sidebar to whatever your own
experience shows.
""")
