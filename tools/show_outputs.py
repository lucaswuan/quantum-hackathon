"""Print the text outputs of every code cell in mic_planner.ipynb (for review without Jupyter)."""

import os
import sys

import nbformat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
nb = nbformat.read(os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "mic_planner.ipynb"), as_version=4)
for i, c in enumerate(nb.cells):
    if c.cell_type != "code":
        continue
    print(f"--- cell {i} ---")
    for o in c.get("outputs", []):
        if o.output_type == "stream":
            print(f"[{o.name}]", o.text.rstrip())
        elif o.output_type == "error":
            print("[ERROR]", o.ename, o.evalue)
        elif o.output_type in ("execute_result", "display_data"):
            data = o.get("data", {})
            if "text/markdown" in data:
                print("[markdown]", data["text/markdown"])
            elif "image/png" in data:
                print("[image]")
            elif "text/plain" in data:
                print("[text]", data["text/plain"][:300])
