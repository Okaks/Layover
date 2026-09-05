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

    cur, best = ctx["current"], ctx["best"]
    rts, sym = ctx["routes"], ctx["symbol"]
    saves = ctx["diff"] > 0

    # ---- title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _bar(s)
    _box(s, MARGIN, Emu(457200), Emu(5486400), Emu(274320), "LAYOVER", 10, GOLD, bold=True)
    _box(s, MARGIN, Emu(2377440), Emu(10972800), Emu(1645920),
         ["What this transfer", "actually costs"], 48, CREAM, bold=True, font="Georgia")
    _box(s, MARGIN, Emu(4114800), Emu(10972800), Emu(365760),
         f"{len(rts)} routes compared on total cost per transfer", 14, GOLD)
    _rule(s, MARGIN, Emu(4617720))
    _box(s, MARGIN, Emu(4754880), Emu(10972800), Emu(365760),
         "The fee is visible. The exchange rate margin is not.", 13, MUTED)
    _box(s, Emu(8229600), Emu(6400800), Emu(3474720), Emu(274320),
         date.today().strftime("%-d %B %Y"), 9, MUTED, align=PP_ALIGN.RIGHT)

    # ---- 01 the numbers
    _section(prs, "01", "THE NUMBERS", "WHAT THE NUMBERS SHOW",
             [f"Payment size {_money(ctx['amount'])}, {ctx['per_month']} times a month — "
              f"{ctx['per_year']} transfers a year. Market rate {sym}{ctx['market']:,.0f}."] +
             [f"{r['name']} — fee {_money(r['fee'])} ({r['fee_pct']:.2f}%), rate {sym}{r['rate']:,.0f} "
              f"giving a margin of {_money(r['spread'])} ({r['spread_pct']:.2f}%). "
              f"Total {_money(r['total'])} per transfer, {_money(r['annual'])} a year. "
              f"Settles in {r['days']:.2g} days."
              for r in rts] +
             [f"Cheapest: {best['name']} at {_money(best['total'])} per transfer."])

    # ---- 02 implication
    _section(prs, "02", "IMPLICATION", "WHAT IT MEANS", [
        f"On the current route the fee is {_money(cur['fee'])} and the exchange rate margin is "
        f"{_money(cur['spread'])} — a rate of {sym}{cur['rate']:,.0f} against {sym}{ctx['market']:,.0f}.",

        "The margin does not appear on a statement. It is priced into the rate, which is why most finance "
        "teams know the fee precisely and have never seen the margin written down.",

        f"Across {ctx['per_year']} transfers a year the margin alone accounts for "
        f"{_money(cur['spread'] * ctx['per_year'])}.",
    ] + ([f"Capital in transit adds {_money(cur['carry'])} a year at {ctx['rate_pct']}% cost of capital."]
         if ctx["show_capital"] else []) + (
        [f"Moving to {best['name'].lower()} would change the annual cost by "
         f"{_money(abs(ctx['diff']))}, or {abs(ctx['diff_pct']):.0f}%."] if saves else
        ["The current route is already the cheapest of those compared. The remaining differences are "
         "settlement time and how pricing is set."]),
    )

    # ---- 03 recommendation
    _section(prs, "03", "RECOMMENDATION", "WHAT TO DO WITH THIS", [
        "Ask for the market rate alongside every quote. A rate given without a reference point cannot be "
        "assessed, and the margin is usually the larger of the two costs.",

        f"Compare total cost rather than fees. On the current route the fee is "
        f"{100*cur['fee']/max(cur['total'],1):.0f}% of what the transfer actually costs.",

        "Weigh how pricing is set, not only what it is. Published pricing holds across a quarter end and "
        "a public holiday; a negotiated rate moves with the relationship and the day.",

        "Establish when verification happens. Documentation held once at onboarding is a condition of "
        "access. Documentation requested at payment time is a delay on every transfer.",

        "Regulated settlement infrastructure is a different proposition from a cheaper transfer. Local "
        "licensing, published pricing, continuous settlement and verification held in advance are "
        "structural, and they hold whether or not a given transfer prices lower.",
    ])

    # ---- 04 inputs
    _section(prs, "04", "INPUTS USED", "INPUTS USED",
             [f"Payment size: {_money(ctx['amount'])}",
              f"Payments per month: {ctx['per_month']}",
              f"Market rate: {sym}{ctx['market']:,.0f} per USD"] +
             [f"{r['name']}: fee {r['fee_pct']:.2f}%, rate {sym}{r['rate']:,.0f}, {r['days']:.2g} days"
              for r in rts] +
             [f"Cost of capital: {ctx['rate_pct']}% a year" if ctx["show_capital"]
              else "Capital in transit: not priced", "",
              "Every route is entered rather than assumed. Settlement timings reference a primary "
              "interview with a serving treasury analyst at a Nigerian fintech, August 2026."])

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()
