import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_notebook_carries_the_current_package():
    nb = json.loads((ROOT / "mic_planner.ipynb").read_text(encoding="utf-8"))
    embedded = {}
    for cell in nb["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.startswith("%%writefile"):
            head, body = source.split("\n", 1)
            embedded[Path(head.split()[1]).name] = body
    package = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "micplanner").glob("*.py")}
    assert embedded == package
