"""Build slides/mic_planner_deck.pptx and slides/deck_outline.md with python-pptx.

Run from the project folder after tools/make_figures.py: python tools/build_slides.py
Numbers come from figures/numbers.json, which make_figures.py writes from code runs.
"""

import json
import os

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
NUM = json.load(open(os.path.join(FIG, "numbers.json")))

FONT = "Calibri"
MONO = "Courier New"
INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
MUTED = RGBColor(0x89, 0x87, 0x81)
ACCENT = RGBColor(0x2A, 0x78, 0xD6)
LIGHT = RGBColor(0xFC, 0xFC, 0xFB)
CARD = RGBColor(0xF0, 0xEF, 0xEC)
DARK = RGBColor(0x16, 0x1B, 0x24)
DARK_CARD = RGBColor(0x24, 0x2B, 0x37)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_WHITE = RGBColor(0xC9, 0xCE, 0xD6)

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.6)

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
TITLE_ONLY = prs.slide_layouts[5]
outline = []


def pct(x, digits=1):
    return f"{100 * x:.{digits}f}%"


# ---------------------------------------------------------------------------
# helpers

def new_slide(title, dark=False, size=36):
    s = prs.slides.add_slide(TITLE_ONLY)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = DARK if dark else LIGHT
    t = s.shapes.title
    t.left, t.top, t.width, t.height = MARGIN, Inches(0.4), W - 2 * MARGIN, Inches(0.95)
    tf = t.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = title
    r.font.name, r.font.size, r.font.bold = FONT, Pt(size), True
    r.font.color.rgb = WHITE if dark else INK
    outline.append({"title": title, "body": [], "notes": ""})
    return s


def _bullet(p, indent=0.32):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Emu(Inches(indent))))
    pPr.set("indent", str(-Emu(Inches(indent))))
    for tag in ("a:buNone", "a:buAutoNum", "a:buChar", "a:buFont"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    f = etree.SubElement(pPr, qn("a:buFont"))
    f.set("typeface", "Arial")
    c = etree.SubElement(pPr, qn("a:buChar"))
    c.set("char", "•")


def text(slide, x, y, w, h, paras, size=20, color=INK, bold=False, bullets=False, font=FONT, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, space_after=8, record=True, line_spacing=None):
    """paras: list of strings or lists of (text, {bold, color, size, font}) runs."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        if line_spacing:
            p.line_spacing = line_spacing
        runs = para if isinstance(para, list) else [(para, {})]
        for chunk, opt in runs:
            r = p.add_run()
            r.text = chunk
            r.font.name = opt.get("font", font)
            r.font.size = Pt(opt.get("size", size))
            r.font.bold = opt.get("bold", bold)
            r.font.color.rgb = opt.get("color", color)
        if bullets:
            _bullet(p)
        if record:
            outline[-1]["body"].append(("- " if bullets else "") + "".join(c for c, _ in runs))
    return tb


def box(slide, x, y, w, h, fill=CARD, radius=0.06):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def picture(slide, name, x, y, w=None, h=None, alt=""):
    pic = slide.shapes.add_picture(os.path.join(FIG, name), x, y, width=w, height=h)
    pic._element.nvPicPr.cNvPr.set("descr", alt)
    outline[-1]["body"].append(f"[figure: figures/{name}] {alt}")
    return pic


def stat(slide, x, y, w, number, label, dark=False, num_size=48, label_size=18):
    text(slide, x, y, w, Inches(0.9), [number], size=num_size, bold=True, color=ACCENT, record=False)
    text(slide, x, y + Inches(0.85), w, Inches(0.9), [label], size=label_size, color=SOFT_WHITE if dark else INK2,
         record=False)
    outline[-1]["body"].append(f"{number}: {label}")


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body
    outline[-1]["notes"] = body


def stems(slide, x0, y_base, heights, gap=0.32):
    """The deck's motif: a little spectrum of mic stems (blue) and product stems (grey)."""
    for i, (hgt, is_mic) in enumerate(heights):
        r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x0 + Inches(i * gap), y_base - Inches(hgt),
                                   Inches(0.07 if is_mic else 0.04), Inches(hgt))
        r.fill.solid()
        r.fill.fore_color.rgb = ACCENT if is_mic else MUTED
        r.line.fill.background()
        r.shadow.inherit = False


MOTIF = [(0.5, 0), (0.5, 0), (1.5, 1), (0.5, 0), (1.5, 1), (0.5, 0), (0.5, 0), (1.5, 1), (0.5, 0),
         (0.5, 0), (0.5, 0), (1.5, 1), (0.5, 0), (1.5, 1), (0.5, 0), (0.5, 0)]

story = NUM["story_plan_mhz"]
card = NUM["resource_card"]
qubo = NUM["qubo"]
cvar = NUM["cvar_clean_by_p"]

# ---------------------------------------------------------------------------
# 1. Title
s = new_slide("IM-free wireless mic planner", dark=True, size=48)
s.shapes.title.top = Inches(1.7)
text(s, MARGIN, Inches(2.75), Inches(9.5), Inches(1.4),
     ["Describe the venue in plain words. Get mic frequencies with no intermodulation hits, found with QAOA."],
     size=26, color=SOFT_WHITE)
text(s, MARGIN, Inches(4.55), Inches(9.0), Inches(1.4),
     [[("[Team name]", {"bold": True, "color": WHITE})], "[Member 1], [Member 2], [Member 3], [Member 4]",
      "Qiskit Fall Fest 2026, University of Waterloo"], size=20, color=SOFT_WHITE, space_after=4)
stems(s, Inches(8.3), Inches(7.0), MOTIF)
notes(s, "Hi, we're [Team name]. Our project turns a real sound-engineering headache into a quantum "
         "optimization problem. When several wireless mics transmit at once, they create ghost signals that can "
         "land on other mics and make them crackle. Our tool lets someone describe their venue in plain words, "
         "and it returns a frequency plan with no ghost hits, found with QAOA on Qiskit. We'll be upfront: "
         "this is a modelling contribution, not a speed-up.")

# 2. The problem
s = new_slide("Two mics on stage make two ghost signals")
text(s, MARGIN, Inches(1.45), Inches(12), Inches(1.6),
     ["Mics at f1 and f2 mix and create third-order products at 2f1 − f2 and 2f2 − f1",
      "A third mic tuned to a ghost picks it up as noise or crackle",
      "Most manufacturers recommend at least 250 kHz between any product and any mic (Shure)"],
     size=20, bullets=True, space_after=6)
picture(s, "fig_ghost_example_slide.png", Inches(0.9), Inches(3.3), w=Inches(11.5),
        alt="Two mics at 470.50 and 471.25 MHz create products at 469.75 and 472.00 MHz.")
notes(s, "Here's the physics in one picture. Two mics at 470.50 and 471.25 megahertz. Their signals mix "
         "inside the electronics, and third-order products appear at two f1 minus f2 and two f2 minus f1: "
         "469.75 and 472.00. If we put a third mic at 472.00, it hears that ghost. Shure's guide says most "
         "manufacturers recommend keeping every third-order product at least 250 kilohertz from every carrier. "
         "That's the rule our tool enforces.")

# 3. Why it's hard
s = new_slide("Products grow with the cube of the mic count")
stat(s, MARGIN, Inches(1.6), Inches(3.6), "50", "third-order products from just 5 mics")
stat(s, MARGIN, Inches(3.3), Inches(3.6), "31,200", "from 40 mics, a size pros run routinely (SoundPro)")
text(s, MARGIN, Inches(5.2), Inches(3.9), Inches(1.8),
     ["Pros use vendor software (Shure Wireless Workbench, Sennheiser WSM, PWS IAS) or an RF coordinator"],
     size=18, color=INK2)
picture(s, "fig_product_growth_slide.png", Inches(4.75), Inches(1.6), w=Inches(8.0),
        alt="Two-tone and three-tone third-order product counts from 3 to 40 mics, log scale.")
notes(s, "Why is planning hard? The number of products explodes. n carriers make n times n minus 1 two-tone "
         "products and n choose 2 times n minus 2 three-tone products. Five mics already make 50. Forty mics "
         "make 31,200, and SoundPro's 2026 guide says coordinated systems routinely run 40 or more channels. "
         "Professionals use vendor tools like Shure Wireless Workbench, which is free, Sennheiser WSM or PWS "
         "IAS, or they hire an RF coordinator. Every count on this slide comes from our own code.")

# 4. Our tool
s = new_slide("Our tool: describe the venue, get a clean plan")
code_box = box(s, MARGIN, Inches(1.5), Inches(7.2), Inches(1.65), fill=DARK)
text(s, MARGIN + Inches(0.25), Inches(1.68), Inches(6.8), Inches(1.4),
     ['plan_mics(band="470-474 MHz", mics=5,', '          step="250 kHz", spacing="500 kHz",',
      '          im_guard="250 kHz")'], size=18, font=MONO, color=WHITE, space_after=2)
text(s, Inches(8.2), Inches(1.4), Inches(4.6), Inches(2.3),
     ["For a school AV tech or theatre sound designer", "No QUBO, Hamiltonian, penalty or mixer in sight",
      "Returns the plan, a report, a spectrum and a CSV"], size=18, bullets=True, space_after=6)
picture(s, "fig_plan_story.png", Inches(0.7), Inches(3.75), w=Inches(11.9),
        alt="QAOA plan " + ", ".join(f"{f:.2f}" for f in story) + " MHz with all products clear of the mics.")
text(s, MARGIN, Inches(7.0), Inches(12), Inches(0.4),
     ["Story: five of the Humanities Theatre's six Shure channels (seats 721). The band is illustrative."],
     size=14, color=MUTED)
notes(s, "This is the whole interface. You say the band, how many mics, the grid step, the spacing and the "
         "guard, in plain units. Our story is the Humanities Theatre in Hagey Hall, which seats up to 721 and "
         "lists three Shure ULD handhelds and three body-packs. We plan five of those six channels. The venue "
         "pages don't give frequency bands, so 470 to 474 megahertz is illustrative. The tool returned "
         + ", ".join(f"{f:.2f}" for f in story) + " megahertz. Every grey product line misses every blue mic. "
         "It also writes a CSV.")

# 5. The bridge
s = new_slide("The bridge: planning rules become qubit interactions")
steps = [("Rules", "Mics 500 kHz apart. No product within 250 kHz of a mic."),
         ("Conflict sets", "15 close pairs, 56 triples (2fₖ − fₗ), 252 quadruples (fₖ + fₗ − fₚ)"),
         ("Cost on 16 qubits", f"x = (1 − Z)/2 gives {sum(NUM['z_strings'].values())} Z-strings, up to 4 Z's each"),
         ("QAOA", "Dicke start and XY mixer keep exactly 5 mics in every sample")]
bw, gap = Inches(2.75), Inches(0.37)
for i, (head, body) in enumerate(steps):
    x = MARGIN + i * (bw + gap)
    box(s, x, Inches(1.55), bw, Inches(2.15))
    text(s, x + Inches(0.2), Inches(1.7), bw - Inches(0.4), Inches(0.5), [f"{i + 1}. {head}"], size=20, bold=True,
         color=ACCENT, record=False)
    text(s, x + Inches(0.2), Inches(2.25), bw - Inches(0.4), Inches(1.4), [body], size=18, color=INK, record=False)
    outline[-1]["body"].append(f"{i + 1}. {head}: {body}")
    if i < 3:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + bw + Inches(0.06), Inches(2.48), Inches(0.25), Inches(0.3))
        a.fill.solid()
        a.fill.fore_color.rgb = MUTED
        a.line.fill.background()
box(s, MARGIN, Inches(4.0), W - 2 * MARGIN, Inches(0.95), fill=DARK)
text(s, MARGIN + Inches(0.3), Inches(4.17), W - 2 * MARGIN - Inches(0.6), Inches(0.7),
     ["C(x) = Σ close pairs xₖxₗ + Σ triples xₖxₗxₘ"
      " + Σ quadruples xₖxₗxₚxₘ,   with exactly 5 mics"],
     size=20, color=WHITE)
text(s, MARGIN, Inches(5.25), Inches(12), Inches(2.0),
     ["A plan is IM-free exactly when its cost is 0",
      "Three- and four-way IM rules go in directly as 3- and 4-qubit Z terms",
      "The mic count is fixed by the circuit, so there is no penalty weight to tune"],
     size=20, bullets=True, space_after=8)
notes(s, "Here's the bridge. Each allowed frequency is a qubit: 1 means a mic sits there. The rules become "
         "three kinds of conflict: close pairs, triples where a two-tone product lands on a third mic, and "
         "quadruples where a three-tone product lands on a fourth. Substituting x equals one minus Z over two "
         "gives a diagonal Hamiltonian with 948 Z-strings. QAOA starts in a Dicke state, every five-mic plan "
         "with equal weight, and the XY mixer only swaps a one and a zero, so it moves mics but never adds or "
         "removes one. No penalty weights. The circuit is built with Qiskit's qaoa_ansatz function.")

# 6. Demo
s = new_slide("Demo: even spacing is the worst case")
picture(s, "fig_newcomer_vs_qaoa.png", MARGIN, Inches(1.35), w=Inches(9.3),
        alt="Evenly spaced plan with 20 products on mics, above the QAOA plan with none.")
nc = NUM["newcomer_counts"]
stat(s, Inches(10.2), Inches(1.6), Inches(2.6), str(sum(nc.values())), "hits for evenly spaced mics")
stat(s, Inches(10.2), Inches(3.4), Inches(2.6), "0", "hits for the QAOA plan")
text(s, Inches(10.2), Inches(5.2), Inches(2.6), Inches(1.8),
     ["Greedy also finds a clean plan here. We say so."], size=18, color=INK2)
notes(s, "What does a newcomer do? Often they space the mics evenly. That's the worst case. Evenly spaced "
         f"carriers are full of arithmetic progressions, and each one drops a product right on a mic: {nc['two-tone']} "
         f"two-tone hits and {nc['three-tone']} three-tone hits, shown as red crosses. The QAOA plan below has none. "
         "To be fair, a simple greedy method also finds a clean plan on this instance, so our bad example is "
         "the newcomer's plan, not greedy's.")

# 7. How well it works
s = new_slide("How well it works: QAOA against random plans")
stat(s, MARGIN, Inches(1.5), Inches(3.8), pct(NUM["story_clean_share"]),
     "of 8,000 QAOA samples are IM-free (p = 3)")
stat(s, MARGIN, Inches(3.15), Inches(3.8), pct(NUM["clean_share"], 2),
     f"of random plans are IM-free ({NUM['clean']} of {NUM['plans']:,})")
stat(s, MARGIN, Inches(4.8), Inches(3.8), pct(cvar[4], 0),
     "at p = 5 on our exact simulation, not run on the circuit")
picture(s, "fig_histogram_slide.png", Inches(4.75), Inches(1.9), w=Inches(8.0),
        alt="QAOA samples concentrate at zero and one conflict compared with uniform random plans.")
notes(s, "How well does it work? With three layers, 7.1 percent of 8,000 samples from Qiskit's "
         "StatevectorSampler are IM-free. A random five-mic plan is IM-free 0.55 percent of the time, so "
         "that's about 13 times better. The exact probability from our simulation is 6.96 percent, so the "
         "sampler agrees. CVaR beat the plain average as the training objective. On our exact NumPy simulation, "
         "five layers reach 12 percent, but we only ran three on the circuit to keep the notebook fast. "
         "This gain is real but modest.")

# 8. Why quantum, honestly
s = new_slide("Why quantum, honestly")
cards = [("No speed-up", f"{NUM['plans']:,}",
          f"plans, all checked by brute force in about 10 ms. Annealing ends clean in {NUM['sa_clean_runs']} of 50 runs."),
         ("A modelling fit", f"{qubo['qubits']} vs {qubo['variables']}",
          "qubits here vs variables as a QUBO. No auxiliary variables, no count penalty."),
         ("The price", f"{card['full']['cx']:,}", "CNOTs at p = 3. Four-way terms cost circuit depth.")]
cw = Inches(3.85)
for i, (head, big, body) in enumerate(cards):
    x = MARGIN + i * (cw + Inches(0.28))
    box(s, x, Inches(1.5), cw, Inches(3.75))
    text(s, x + Inches(0.3), Inches(1.7), cw - Inches(0.6), Inches(0.5), [head], size=20, bold=True, color=INK2,
         record=False)
    text(s, x + Inches(0.3), Inches(2.3), cw - Inches(0.6), Inches(1.0), [big], size=48, bold=True, color=ACCENT,
         record=False)
    text(s, x + Inches(0.3), Inches(3.4), cw - Inches(0.6), Inches(2.0), [body], size=18, color=INK, record=False)
    outline[-1]["body"].append(f"{head}: {big}. {body}")
text(s, MARGIN, Inches(5.9), Inches(12), Inches(1.0),
     ["We found no earlier quantum approach that models IM products."], size=22, bold=True, color=INK)
notes(s, "Why quantum? Three honest answers. First, there's no speed-up: brute force solves this in about 10 "
         "milliseconds, and simulated annealing ends clean in 50 of 50 runs. Second, a modelling fit: the IM "
         f"rules are three- and four-way, and QAOA takes them as is on 16 qubits. A QUBO needs {qubo['variables']} "
         f"variables after greedy Rosenberg substitution, {qubo['best_variables']} to {qubo['worst_variables']} "
         "depending on tie-breaks, plus a penalty for the mic count. Third, the price: the four-way terms make the "
         f"circuit deep, {card['full']['cx']:,} CNOTs at three layers. And we found no earlier quantum approach "
         "that models IM products. D-Wave's frequency example and Vandelli et al. 2025 handle pairwise "
         "interference only.")

# 9. Where it falls short
s = new_slide("Where it falls short")
text(s, MARGIN, Inches(1.45), Inches(7.6), Inches(5.5),
     ["Classically trivial at 16 frequencies, and greedy solves it",
      "Here it is a Golomb-ruler search, a link known since 1953 (Babcock)",
      "Third-order only: no fifth order, TV data, power or distance",
      "Angles tuned by exact simulation, which does not scale",
      f"{card['full']['cx']:,} CNOTs at p = 3, and not run on hardware"],
     size=20, bullets=True, space_after=12)
box(s, Inches(8.6), Inches(1.5), Inches(4.13), Inches(4.5), fill=CARD)
text(s, Inches(8.9), Inches(1.7), Inches(3.6), Inches(0.5), ["Beyond the toy size"], size=20, bold=True,
     color=INK2, record=False)
stat(s, Inches(8.9), Inches(2.3), Inches(3.6), f"{NUM['six_mic_points']}",
     f"grid points for 6 mics, with just {NUM['six_mic_clean']} clean plans", label_size=18)
stat(s, Inches(8.9), Inches(4.2), Inches(3.6), "782+", "qubits for 40 mics on this grid, with 39.6 million 4-qubit terms",
     label_size=18)
notes(s, "Where it falls short. At this size every classical method wins. On this grid with exact landings, "
         "an IM-free plan is a Golomb ruler with no gap of one, and Babcock linked IM to these rulers in 1953. "
         "We only model third-order products, with no fifth-order, no TV channel data and no transmitter "
         "power or distance. We tuned the angles with an exact classical simulation, which can't scale. The "
         "circuit is deep. Beyond the toy size: six mics need 21 grid points and only two plans work; forty "
         "mics on this kind of grid need at least 782 qubits and about 39.6 million four-qubit terms.")

# 10. What's next
s = new_slide("What's next")
nexts = [("Fifth-order products", "Shure lists them as in-band too. Add 5-body terms or a guard margin."),
         ("Real venues", "Receiver tuning ranges, local TV channels, several bands and rooms."),
         ("Scale", "Sparser models and problem decomposition for 40 or more mics."),
         ("Hardware", f"A p = 1 run with the leaner {card['cost_layer_single_gate']['cx']:,}-CNOT cost layer.")]
for i, (head, body) in enumerate(nexts):
    x = MARGIN + i * (Inches(2.85) + Inches(0.23))
    box(s, x, Inches(1.6), Inches(2.85), Inches(3.4))
    text(s, x + Inches(0.22), Inches(1.75), Inches(2.4), Inches(0.6), [f"{i + 1}"], size=40, bold=True, color=ACCENT,
         record=False)
    text(s, x + Inches(0.22), Inches(2.5), Inches(2.4), Inches(0.5), [head], size=20, bold=True, color=INK,
         record=False)
    text(s, x + Inches(0.22), Inches(3.05), Inches(2.4), Inches(1.9), [body], size=18, color=INK2, record=False)
    outline[-1]["body"].append(f"{i + 1}. {head}: {body}")
stems(s, Inches(8.3), Inches(7.0), MOTIF)
notes(s, "What's next. First, fifth-order products, which Shure also lists as in-band. Second, real venues: "
         "actual receiver tuning ranges, local TV channel data, and several bands or rooms at once. Third, scale: "
         "the full model grows too fast, so we'd need sparser models or to split the problem. Fourth, hardware: "
         f"synthesizing the whole cost layer as one gate cuts it to {card['cost_layer_single_gate']['cx']:,} "
         "CNOTs, which is a start for a one-layer test.")

# 11. Team contributions
s = new_slide("Team contributions", dark=True)
team = [("[Member 1]", "Problem and engine", "RF rules, IM enumeration, checker, brute force"),
        ("[Member 2]", "Quantum circuit", "Cost operator, Dicke state, XY mixer, QAOA"),
        ("[Member 3]", "Results and baselines", "Tuning, sampling, classical baselines, figures"),
        ("[Member 4]", "Story and demo", "plan_mics interface, venue story, slides, live demo")]
for i, (who, role, what) in enumerate(team):
    x = MARGIN + i * (Inches(2.85) + Inches(0.23))
    box(s, x, Inches(1.7), Inches(2.85), Inches(3.3), fill=DARK_CARD)
    text(s, x + Inches(0.22), Inches(1.9), Inches(2.4), Inches(0.5), [who], size=22, bold=True, color=WHITE,
         record=False)
    text(s, x + Inches(0.22), Inches(2.5), Inches(2.4), Inches(0.8), [role], size=20, bold=True, color=ACCENT,
         record=False)
    text(s, x + Inches(0.22), Inches(3.55), Inches(2.4), Inches(1.4), [what], size=18, color=SOFT_WHITE,
         record=False)
    outline[-1]["body"].append(f"{who}: {role}. {what}")
text(s, MARGIN, Inches(5.5), Inches(7.4), Inches(1.4),
     ["Each of us can explain every part. AI tools helped write code and drafts; we checked every number."],
     size=18, color=SOFT_WHITE)
stems(s, Inches(8.3), Inches(7.0), MOTIF)
notes(s, "Placeholder slide: fill in names and adjust roles before Friday. Each role matches one of the four "
         "explainers in the team folder. Say plainly what AI did: it helped write code and first drafts, and "
         "we checked every number against the notebook.")

# 12. References
s = new_slide("References")
refs_left = ["Shure: All about wireless intermodulation distortion",
             "SoundPro: RF coordination for live events, 2026 guide",
             "UW Theatres: Our theatres; Humanities Theatre specs",
             "D-Wave: frequency-selection example (GitHub)",
             "Vandelli, Ferrari, Dragoni, arXiv:2511.15566 (2025)",
             "Shure: Wireless Workbench product page"]
refs_right = ["Farhi, Goldstone, Gutmann, arXiv:1411.4028 (2014)",
              "Hadfield et al., Algorithms 12, 34 (2019)",
              "Wang et al., Phys. Rev. A 101, 012320 (2020)",
              "Bärtschi, Eidenbenz, arXiv:1904.07358 (2019)",
              "Barkoutsos et al., Quantum 4, 256 (2020)",
              "Babcock, Bell Syst. Tech. J. 32, 63 (1953)"]
text(s, MARGIN, Inches(1.45), Inches(6.0), Inches(5.0), refs_left, size=18, color=INK, space_after=10)
text(s, Inches(6.9), Inches(1.45), Inches(5.9), Inches(5.0), refs_right, size=18, color=INK, space_after=10)
text(s, MARGIN, Inches(6.55), Inches(12), Inches(0.5),
     ["Full list with links in mic_planner.ipynb, section 9. Every number in this deck comes from that notebook."],
     size=16, color=MUTED)
notes(s, "Full references with links are in the notebook's last section. Every number on these slides comes "
         "from code in the notebook or from a page we opened and cite here.")

out = os.path.join(ROOT, "slides", "mic_planner_deck.pptx")
os.makedirs(os.path.dirname(out), exist_ok=True)
prs.save(out)

lines = ["# Deck outline: IM-free wireless mic planner", "",
         "Generated by `tools/build_slides.py` from `figures/numbers.json`. Slide text first, then speaker notes.", ""]
for i, sl in enumerate(outline, 1):
    lines += [f"## Slide {i}: {sl['title']}", ""]
    lines += [b if b.startswith("- ") else f"- {b}" for b in sl["body"]]
    lines += ["", f"**Speaker notes.** {sl['notes']}", ""]
open(os.path.join(ROOT, "slides", "deck_outline.md"), "w", encoding="utf-8").write("\n".join(lines))
print("wrote", out, "with", len(prs.slides), "slides")
