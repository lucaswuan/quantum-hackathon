"""Run mic_planner.ipynb alone in an empty temporary folder, as a judge would, and save the outputs back.

The saved outputs then come from the code embedded in the notebook, not from the micplanner folder.
Run from the project folder: python tools/run_standalone.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK = os.path.join(ROOT, "mic_planner.ipynb")

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    copy = shutil.copy(NOTEBOOK, tmp)
    t0 = time.perf_counter()
    subprocess.run([sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                    "mic_planner.ipynb", "--ExecutePreprocessor.timeout=900"], cwd=tmp, check=True)
    seconds = time.perf_counter() - t0
    shutil.copy(copy, NOTEBOOK)
print(f"Ran alone in {seconds:.0f} s and saved the outputs to mic_planner.ipynb")
