print("SCRIPT STARTER")

import sys
print("sys.path OK")

import os
print("os import OK")

from pathlib import Path
print("pathlib import OK")

ROOT = Path(__file__).resolve().parent.parent
print("ROOT:", ROOT)

SCRAPERS_DIR = ROOT / "src" / "scrapers"
print("SCRAPERS_DIR:", SCRAPERS_DIR)

sys.path.append(str(SCRAPERS_DIR))
print("sys.path updated")

print("Prøver å importere utils_files...")

from utils_files import load_all_postliste_from_shards
print("utils_files import OK")

print("SCRIPT FERDIG")
