"""Export every slide of the deck to PNG through PowerPoint (Windows COM), for the overflow check.

Needs Microsoft PowerPoint and `pip install comtypes`. Output goes to slides/render/ (git-ignored).
Run from the project folder: python tools/render_slides.py
"""

import os
import sys

import comtypes.client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
deck = os.path.join(ROOT, "slides", sys.argv[1] if len(sys.argv) > 1 else "mic_planner_deck.pptx")
out = os.path.join(ROOT, "slides", "render")
os.makedirs(out, exist_ok=True)

app = comtypes.client.CreateObject("PowerPoint.Application")
try:
    pres = app.Presentations.Open(deck, True, False, False)  # read-only, untitled off, no window
    for i in range(1, pres.Slides.Count + 1):
        pres.Slides(i).Export(os.path.join(out, f"slide-{i:02d}.png"), "PNG", 1600, 900)
    print("exported", pres.Slides.Count, "slides to", out)
    pres.Close()
finally:
    app.Quit()
