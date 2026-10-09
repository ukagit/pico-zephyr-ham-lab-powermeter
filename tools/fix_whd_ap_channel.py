#!/usr/bin/env python3
"""Apply the narrowly scoped WHD WIFI5 AP channel correction, with backup."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("header", type=Path, help="Path to COMPONENT_WIFI5/src/include/whd_chip_constants.h")
args = parser.parse_args()
p = args.header
text = p.read_text()
old = "(((chspec)<=CH_MAX_2G_CHANNEL)"
new = "((CHSPEC_CHANNEL(chspec)<=CH_MAX_2G_CHANNEL)"
if new in text:
    print("Korrektur bereits vorhanden.")
elif text.count(old) == 1:
    backup = p.with_name(p.name + ".before-ap-fix")
    if not backup.exists():
        backup.write_bytes(p.read_bytes())
    p.write_text(text.replace(old, new))
    print("Kanalentscheidung korrigiert; Sicherung:", backup)
else:
    raise SystemExit("Abbruch: erwartete Stelle nicht eindeutig gefunden.")
