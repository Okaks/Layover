"""
Value Date - settlement route simulator.

Models the working capital a company commits early because cross-border
settlement takes time, plus the exposure created when payments are held for
documentation.

Route timings come from a primary interview with a serving treasury analyst at
a Nigerian fintech, August 2026. Every input is editable on the page.
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
  .assume {background:#17212F; border-radius:4px; padding:0.85rem 1rem; color:#8FA3BF;
           font-size:0.85rem; line-height:1.6;}
</style>
""", unsafe_allow_html=True)

ROUTE_DEFAULTS = {
    "local_dom": {
        "name": "Local domiciliary account",
        "sub": "Instruction to a local bank, settling cross-currency",
        "days": 2.0, "lo": 1.0, "hi": 3.0, "hold": 22,
        "spread": 2.0,
        "basis": ("Once it crosses currencies it is T+1 at best and can be T+2 or T+3. The bank may process "
                  "within the hour if pressed, or at end of day if not - and that depends on relationship, "
                  "not on anything the company controls."),
    },
    "offshore": {
        "name": "Offshore account, matched currency",
        "sub": "Paying from a USD account into a USD beneficiary",
        "days": 0.3, "lo": 0.1, "hi": 1.0, "hold": 8,
        "spread": 0.9,
        "basis": ("A US offshore account paying into the US lands same day, usually within hours. Requires "
                  "holding the currency in the right place before the invoice arrives."),
    },
    "stablecoin": {
        "name": "Stablecoin settlement rail",
        "sub": "Local currency in, stablecoin transport, local payout",
        "days": 0.15, "lo": 0.05, "hi": 0.5, "hold": 6,
        "spread": 0.45,
        "basis": ("Settles continuously rather than on banking hours. Verification sits with a regulated "
                  "counterparty holding the company's details from onboarding."),
    },
}

HOLD_PRESETS = {
    "Baseline assumption": {"local_dom": 22, "offshore": 8, "stablecoin": 6},
    "Low friction": {"local_dom": 10, "offshore": 4, "stablecoin": 3},
    "High friction": {"local_dom": 35, "offshore": 15, "stablecoin": 10},
}

st.title("What settlement time costs you")
st.markdown(
    '<p class="lede">Few companies send a payment and wait. They release it early and plan around the '
    'delay - which means the money leaves the business before it needed to. This models what that '
    'early release costs, and what happens when a payment is held for documentation.</p>',
    unsafe_allow_html=True,
)

st.sidebar.markdown("### Your payment profile")
st.sidebar.caption("Set these to your own figures. Every number on the page is built from what you enter here.")

amount = st.sidebar.number_input(
    "Typical size of one payment (USD)", 1_000, 50_000_000, 250_000, 10_000,
    help="A single transaction, not a monthly or annual total.",
)
per_month = st.sidebar.slider("Payments per month", 1, 500, 12)

current_route = st.sidebar.selectbox(
    "How you pay today",
    ["local_dom", "offshore", "stablecoin"],
    format_func=lambda k: ROUTE_DEFAULTS[k]["name"],
)
lead_days = st.sidebar.slider(
    "Days you release payment ahead of the due date", 0.0, 21.0, 5.0, 0.5,
    help="How far in advance you send today, so the supplier is paid on time.",
)
margin_mode = st.sidebar.radio(
    "How you decide that lead time",
    ["Derive it from my current route", "I hold a fixed number of days"],
    help="Either the model works out the cover you hold above settlement, or you state it directly.",
)
fixed_margin = None
if margin_mode.startswith("I hold"):
    fixed_margin = st.sidebar.slider("Days of cover you hold, whatever the route", 0.0, 14.0, 2.0, 0.5)

scale_margin = st.sidebar.checkbox(
    "Scale cover to how unpredictable each route is", value=True,
    help="Cover exists because a route varies, not because it is slow. A route with a tight, "
         "predictable window needs less of it.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Your conditions")
rate = st.sidebar.slider("Cost of capital, annual (%)", 5.0, 40.0, 22.0, 0.5,
                         help="What working capital costs you - your borrowing cost, or local money-market rates.")
stall_cost_days = st.sidebar.slider("Days added when a payment is held", 1, 30, 7)

st.sidebar.markdown("---")
st.sidebar.markdown("### Payment hold rate")
hold_mode = st.sidebar.radio(
    "Source", ["Baseline assumption", "Low friction", "High friction", "Enter your own"],
    help="The share of payments delayed for documentation. Use your own figure if you know it.",
)

st.sidebar.markdown("---")
edit_timings = st.sidebar.checkbox("Edit route timings", value=False,
                                   help="Adjust if your own experience differs from the defaults.")

routes = {k: dict(v) for k, v in ROUTE_DEFAULTS.items()}

if hold_mode == "Enter your own":
    st.sidebar.caption("Percentage of payments held for documentation")
    for k in routes:
        routes[k]["hold"] = st.sidebar.slider(
            routes[k]["name"], 0, 60, ROUTE_DEFAULTS[k]["hold"], 1, key=f"h_{k}")
else:
    for k in routes:
        routes[k]["hold"] = HOLD_PRESETS[hold_mode][k]

if edit_timings:
    st.sidebar.caption("Days to land")
    for k in routes:
        routes[k]["days"] = st.sidebar.number_input(
            routes[k]["name"], 0.0, 30.0, float(ROUTE_DEFAULTS[k]["days"]), 0.05, key=f"d_{k}")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Route timings come from a primary interview with a serving treasury analyst at a Nigerian fintech, "
    "August 2026. Hold rates are modelling assumptions, adjustable above. Cost of capital and lead time "
    "are yours to set - no assumption is hidden inside the model."
)

daily_rate = rate / 100 / 365
annual_volume = amount * per_month * 12


def expected_settlement(r):
    """Days the money is genuinely in transit, including documentation holds."""
    return r["days"] + (r["hold"] / 100) * stall_cost_days


current_expected = expected_settlement(routes[current_route])
base_margin = (fixed_margin if fixed_margin is not None
               else max(0.0, lead_days - current_expected))
current_spread = routes[current_route].get("spread", 1.0) or 1.0


def margin_for(r):
    """Cover exists because a route varies, not because it is slow. Where the
    variance is tighter, the same protection needs fewer days."""
    if not scale_margin:
        return base_margin
    ratio = (r.get("spread", 1.0) or 1.0) / current_spread
    return base_margin * min(1.0, ratio)


def capital(days):
    return amount * per_month * (days / 30)


def evaluate(r):
    transit = expected_settlement(r)
    margin = margin_for(r)
    required_lead = transit + margin
    cap_transit, cap_margin = capital(transit), capital(margin)
    return {
        "settle": r["days"], "expected_settle": transit, "margin_days": margin,
        "required_lead": required_lead,
        "cap_transit": cap_transit, "cap_margin": cap_margin,
        "capital": cap_transit + cap_margin,
        "cost_transit": cap_transit * daily_rate * 365,
        "cost_margin": cap_margin * daily_rate * 365,
        "annual_cost": (cap_transit + cap_margin) * daily_rate * 365,
        "days_freed": lead_days - required_lead,
        "held_per_year": (r["hold"] / 100) * per_month * 12,
    }


res = {k: evaluate(v) for k, v in routes.items()}
cheapest = min(res, key=lambda k: res[k]["annual_cost"])
dearest = max(res, key=lambda k: res[k]["annual_cost"])
saving = res[dearest]["annual_cost"] - res[cheapest]["annual_cost"]

st.markdown("---")
h1, h2, h3 = st.columns(3)
cur = res[current_route]
h1.metric("Annual payment volume", f"${annual_volume:,.0f}")
h2.metric("Capital committed on your route", f"${cur['capital']:,.0f}",
          help=f"${cur['cap_transit']:,.0f} in transit plus ${cur['cap_margin']:,.0f} held as cover.")
h3.metric("Annual cost of that capital", f"${cur['annual_cost']:,.0f}",
          delta=f"${cur['annual_cost'] - res[cheapest]['annual_cost']:,.0f} lower on the fastest route",
          delta_color="inverse")

st.markdown("---")
cols = st.columns(3)
for col, (key, r) in zip(cols, routes.items()):
    e = res[key]
    win = " route-win" if key == cheapest else ""
    freed = e["days_freed"]
    margin_txt = (f"{freed:.1f} days earlier than you release today" if freed > 0.05
                  else ("your current policy" if abs(freed) <= 0.05
                        else f"{abs(freed):.1f} days more than you allow today"))
    with col:
        st.markdown(
            f'<div class="route{win}">'
            f'<div class="rname">{r["name"]}</div>'
            f'<div class="rsub">{r["sub"]}</div>'
            f'<div class="unit">Settles in</div>'
            f'<div class="big">{r["days"]:.2g} <span style="font-size:0.95rem">days</span></div>'
            f'<div class="rsub">{e["expected_settle"]:.1f} days once holds are counted</div>'
            f'<div class="unit">Capital committed early</div>'
            f'<div class="big">${e["capital"]:,.0f}</div>'
            f'<div class="rsub">{e["required_lead"]:.1f} days ahead &middot; {margin_txt}</div>'
            f'<div class="unit">Annual cost of that capital</div>'
            f'<div class="big">${e["annual_cost"]:,.0f}</div>'
            f'<div class="rsub">{e["held_per_year"]:.0f} of {per_month*12} payments held for documents</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")
st.markdown(
    '<div class="assume"><b>Cost is one dimension, not the answer.</b> The figures above price working '
    'capital only. Predictability, compliance effort, reconciliation work and how a route behaves on a bad '
    'week may matter more to a finance team than the lowest calculated cost - particularly where a missed '
    'supplier date carries consequences the model cannot see.</div>',
    unsafe_allow_html=True,
)

st.markdown("")
c1, c2, c3 = st.columns(3)
for col, (key, r) in zip([c1, c2, c3], routes.items()):
    with col:
        with st.expander(f"Where the {r['name'].lower()} timing comes from"):
            st.markdown(f'<div class="src">{r["basis"]}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Two costs, not one")

lt1, lt2 = st.columns([1.15, 1])
with lt1:
    st.markdown(
        f"**Capital in transit** is money genuinely moving. On your current route that is "
        f"**{cur['expected_settle']:.1f} days** once documentation holds are counted, costing "
        f"**${cur['cost_transit']:,.0f}** a year. A faster rail reduces this directly.\n\n"
        f"**Capital held as cover** is different. You release **{lead_days:.1f} days** ahead, which is "
        f"**{cur['margin_days']:.1f} days** more than settlement needs. That is not waste - it is "
        f"protection, and it costs **${cur['cost_margin']:,.0f}** a year.\n\n"
        f"Cover exists because a route *varies*, not because it is slow. You hold days because a payment "
        f"*might* take three, not because it takes three. So the thing that shrinks cover is "
        f"predictability rather than speed - a route with a tight, reliable window needs less of it at "
        f"the same average settlement time."
    )
    if not scale_margin:
        st.caption(
            "Cover is currently held constant across routes. Switch on scaling in the sidebar to let a "
            "more predictable route carry less of it."
        )
with lt2:
    st.markdown("**How each route splits**")
    for key, r in routes.items():
        e = res[key]
        st.markdown(
            f'<div style="padding:0.5rem 0; border-bottom:1px solid #1E2836;">'
            f'<b>{r["name"]}</b><br>'
            f'<span class="rsub">in transit {e["expected_settle"]:.1f}d &middot; '
            f'${e["cost_transit"]:,.0f}/yr<br>'
            f'cover {e["margin_days"]:.1f}d &middot; ${e["cost_margin"]:,.0f}/yr</span></div>',
            unsafe_allow_html=True,
        )
    st.caption(
        f"Release {res[cheapest]['required_lead']:.1f} days ahead on the fastest route against "
        f"{cur['required_lead']:.1f} today."
    )

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

st.markdown("---")
with st.expander("Assumptions and method", expanded=False):
    st.markdown(f"""
**Stated assumptions**

*Documentation hold rate - currently {hold_mode.lower()}.* The baseline of 22% on a local domiciliary
account, 8% offshore and 6% on a stablecoin rail is a modelling assumption used to estimate how many
payments may face documentation delays. It is not drawn from published data. Adjust it in the sidebar to
your own experience - the whole model responds.

*Route timings.* Drawn from a primary interview with a serving treasury analyst at a Nigerian fintech,
August 2026: cross-currency settlement from a local domiciliary account at T+1 to T+3, a matched-currency
offshore account landing same day within hours. Editable in the sidebar.

*Lead time, current route, cost of capital, payment size and frequency.* Yours entirely. Nothing is assumed.

*Cover is preserved, never assumed away.* The model does not suggest you release payments later simply
because a route is faster. It takes the cover you hold today and carries it across, so only the settlement
time underneath changes.

*Cover scaling is optional and is an assumption.* With scaling on, a route whose settlement window is
tighter carries proportionally less cover, on the reasoning that cover answers variance rather than speed.
The variance figures behind that are estimates, not measurements. Switch scaling off in the sidebar to
hold cover constant across every route.

**How the numbers are built**

    expected settlement = route days + (hold rate x days added when held)
    expected settlement = route days + (hold rate x days added when held)
    cover held          = your lead time - expected settlement on your current route
                          (or the fixed number of days you state)
    capital in transit  = payment size x payments per month x (settlement days / 30)
    capital as cover    = payment size x payments per month x (cover days / 30)
    annual cost         = (both together) x your cost of capital

Capital committed early is money that has left the business before it was owed. It is an opportunity
cost, not a fee - it never appears on an invoice, which is why it usually goes unpriced.

**What this does not model**

*FX spread.* Spread is negotiated, varies by relationship and by day, and any figure here would be
invented. The tool prices time instead, which is observable.

*Failed payments.* A held payment is modelled as delayed, not lost.

*Route availability.* Whether a company can open an offshore account, or reach a regulated settlement
provider in its market, is a separate question this does not address.

**Why time rather than price.** Fees are visible and get negotiated. Days are invisible, never appear on
an invoice, and cost money every one of them.
""")
