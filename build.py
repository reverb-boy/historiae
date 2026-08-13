#!/usr/bin/env python3
"""Compile the Historiae sources into a single self-contained herodotus-map.html.

Inlines Leaflet (CSS + JS) and the app's own CSS/JS/data into one file, so the
deliverable has no external code dependency. (Map tile *imagery* still streams
from the tile server at runtime — that is the only network need.)
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"


def read(p: pathlib.Path) -> str:
    if not p.exists():
        sys.exit(f"missing source file: {p}")
    return p.read_text(encoding="utf-8")


def main() -> None:
    template = read(SRC / "template.html")

    subs = {
        "{{LEAFLET_CSS}}": read(ROOT / "leaflet.css"),
        "{{APP_CSS}}": read(SRC / "app.css"),
        "{{LEAFLET_JS}}": read(ROOT / "leaflet.js"),
        "{{DATA_JS}}": read(SRC / "data.js"),
        "{{DATA_PLACES_JS}}": read(SRC / "data_places.js"),
        "{{DATA_PERSONS_JS}}": read(SRC / "data_persons.js"),
        "{{DATA_TEXT_JS}}": read(SRC / "data_text.js"),
        "{{APP_JS}}": read(SRC / "app.js"),
    }

    out = template
    for key, val in subs.items():
        if key not in out:
            sys.exit(f"placeholder {key} not found in template.html")
        # str.replace avoids regex issues with $, \, etc. in the payloads
        out = out.replace(key, val)

    # Leaflet resolves marker-image URLs relative to the page; we use no default
    # image markers (divIcon / circleMarker only), so no assets are required.
    kb = len(out.encode("utf-8")) / 1024
    for name in ("herodotus-map.html", "index.html"):   # index.html = GitHub Pages entry
        (ROOT / name).write_text(out, encoding="utf-8")
        print(f"wrote {name}  ({kb:.0f} KB)")
    print(f"  places : {out.count('lat:')}")  # rough sanity signal


if __name__ == "__main__":
    main()
