"""Builds a Layover deck in the DashboardIntel visual system."""

import io
from datetime import date

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

BG = RGBColor(0x0E, 0x0B, 0x08)
GOLD = RGBColor(0xC9, 0xA8, 0x4C)
CREAM = RGBColor(0xF5, 0xED, 0xE0)
MUTED = RGBColor(0x9C, 0x8A, 0x6E)
INK = RGBColor(0x1A, 0x14, 0x10)

W, H = Emu(12192000), Emu(6858000)
PANEL_W = Emu(3474720)
BODY_L = Emu(3840480)
BODY_W = Emu(8046720)
MARGIN = Emu(548640)


def _bg(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG


def _box(slide, l, t, w, h, text, size, color, bold=False, font=None, align=PP_ALIGN.LEFT, space=0):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        if font:
            r.font.name = font
    return tb


def _bar(slide, width=Emu(137160)):
    sh = slide.shapes.add_shape(1, 0, 0, width, H)
    sh.fill.solid()
    sh.fill.fore_color.rgb = GOLD
    sh.line.fill.background()
    sh.shadow.inherit = False


def _rule(slide, l, t, w=Emu(1097280)):
    sh = slide.shapes.add_shape(1, l, t, w, Emu(11430))
    sh.fill.solid()
    sh.fill.fore_color.rgb = GOLD
    sh.line.fill.background()
    sh.shadow.inherit = False


def _section(prs, number, label, heading, paragraphs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    panel = s.shapes.add_shape(1, 0, 0, PANEL_W, H)
    panel.fill.solid()
    panel.fill.fore_color.rgb = GOLD
    panel.line.fill.background()
    panel.shadow.inherit = False

    _box(s, Emu(457200), Emu(2286000), Emu(2743200), Emu(1463040), number, 80, INK, font="Georgia")
    _rule(s, Emu(502920), Emu(3931920), Emu(731520))
    _box(s, Emu(502920), Emu(4114800), Emu(2743200), Emu(1645920), label, 14, INK, bold=True)

    _box(s, BODY_L, Emu(457200), BODY_W, Emu(365760), heading, 13, GOLD, bold=True)
    _box(s, BODY_L, Emu(1097280), BODY_W, Emu(5120640), paragraphs, 14, CREAM, space=14)
    _box(s, BODY_L, Emu(6492240), BODY_W, Emu(274320), "Layover", 8, MUTED)
    return s


def _money(v):
    return f"${v:,.0f}"


def build_deck(ctx):
    """ctx carries every figure and label shown on the page."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    period = ctx["period_label"]
    routes = ctx["routes"]
    worst, best = ctx["worst"], ctx["best"]

    # ---- title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _bar(s)
    _box(s, MARGIN, Emu(457200), Emu(5486400), Emu(274320), "LAYOVER", 10, GOLD, bold=True)
    _box(s, MARGIN, Emu(2377440), Emu(10972800), Emu(1645920),
         ["What settlement time", "costs this business"], 48, CREAM, bold=True, font="Georgia")
    _box(s, MARGIN, Emu(4114800), Emu(10972800), Emu(365760),
         f"Cross-border settlement  ·  {period} view", 14, GOLD)
    _rule(s, MARGIN, Emu(4617720))
    _box(s, MARGIN, Emu(4754880), Emu(10972800), Emu(365760),
         "The fee is visible. The days are not.", 13, MUTED)
    _box(s, Emu(8229600), Emu(6400800), Emu(3474720), Emu(274320),
         date.today().strftime("%-d %B %Y"), 9, MUTED, align=PP_ALIGN.RIGHT)

    # ---- 01 the position
    _section(prs, "01", "THE POSITION", "THE POSITION", [
        f"This business moves {_money(ctx['volume'])} across borders over a {period.lower()} period, "
        f"in payments of about {_money(ctx['amount'])} each.",

        f"Settling through {routes[worst]['name'].lower()} leaves {_money(routes[worst]['capital'])} of "
        f"working capital tied up at any moment — money in transit, plus the buffer held because that "
        f"money is not available while it moves.",

        f"At a {ctx['rate']}% cost of capital, carrying that position costs "
        f"{_money(routes[worst]['cost'])} over the same period.",

        f"On the fastest route the same payment flow ties up {_money(routes[best]['capital'])} and costs "
        f"{_money(routes[best]['cost'])} — a difference of {_money(ctx['saving'])}, or "
        f"{ctx['saving_pct']:.0f}% of the current figure.",
    ])

    # ---- 02 route comparison
    _section(prs, "02", "ROUTE COMPARISON", "ROUTE COMPARISON",
             [f"{r['name']} — settles in {r['days']:.2g} days ({r['range']}). "
              f"Capital tied up {_money(r['capital'])}. Cost {_money(r['cost'])}. "
              f"{r['stalled']:.0f} payments held for documentation."
              for r in routes.values()] + [
                 "Same payment, three routes. The difference is not the fee — it is how long the money is "
                 "unavailable, and how much has to be held on hand because of it."
             ])

    # ---- 03 why time is the cost
    _section(prs, "03", "WHY TIME IS THE COST", "WHY TIME IS THE COST", [
        "Fees appear on an invoice and get negotiated. Days do not appear anywhere.",

        f"Money in transit is money not working. Across a {period.lower()} period, the days a payment "
        f"spends settling are days that capital earns nothing and cannot be deployed.",

        "The buffer compounds it. A business that cannot rely on a payment landing keeps additional "
        "working capital available, and that reserve exists purely because settlement is slow.",

        "Neither figure is a fee, which is why neither is usually priced. Both are real.",
    ])

    # ---- 04 compliance
    _section(prs, "04", "THE COMPLIANCE COST", "THE PART THAT ISN'T ABOUT PRICE", [
        "\"The partners processing these payments mostly aren't local entities. They want the invoice, "
        "the company registration, the payer's details, the source of funds. And most of the time our "
        "people here don't have all of it.\"",

        "— Treasury analyst, Nigerian fintech. Condensed from a primary interview, August 2026.",

        "A payment held for documentation does not get more expensive. It does not happen. That is an "
        "eligibility failure rather than a pricing one, and no rate negotiation fixes it.",

        "Where verification is not already held, the request arrives at payment time — the moment the "
        "money is meant to move.",

        "Under a regulated counterparty, verification happens once at onboarding: due diligence, company "
        "registration, beneficial ownership. Each payment then runs against a business already verified, "
        "so compliance becomes a condition of access rather than a delay on every transfer.",

        f"On the current route, {routes[worst]['stalled']:.0f} of {ctx['payment_count']:.0f} payments are "
        f"held for documentation over this period.",
    ])

    # ---- 05 inputs
    _section(prs, "05", "INPUTS USED", "INPUTS USED", [
        f"Typical payment size: {_money(ctx['amount'])}",
        f"Payments per month: {ctx['per_month']}",
        f"Cost of capital: {ctx['rate']}% a year",
        f"Buffer held against delay: {ctx['buffer_pct']}%" if ctx["holding"]
        else "Approach: payments sent when due, no buffer held",
        f"Days lost when a payment stalls: {ctx['stall_days']}",
        f"Reporting period: {period}",
        "",
        "Route timings come from a primary interview with a serving treasury analyst at a Nigerian "
        "fintech, August 2026. Documentation hold rates are modelling assumptions and are adjustable. "
        "Foreign exchange spread is deliberately not modelled — spread is negotiated and varies by "
        "relationship, so any figure here would be invented. This prices time, which is observable.",
    ])

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()
