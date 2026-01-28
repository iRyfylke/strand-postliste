from pathlib import Path
import sys

print("Python kjører", flush=True)

ROOT = Path(__file__).resolve().parent.parent
print(f"ROOT: {ROOT}", flush=True)

sys.path.append(str(ROOT / "src" / "scrapers"))
print("sys.path oppdatert", flush=True)

print("Prøver å importere utils_files...", flush=True)
import utils_files
print("utils_files import OK", flush=True)
