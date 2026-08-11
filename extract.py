#!/usr/bin/env python3
"""Extract the Herodotus gazetteer from the Perseus Godley TEI.

Perseus tagged every place mention inline as
  <name type="place" key="tgn,NNNN"><reg>Modern [lon,lat] (feature type), …</reg>
     <placeName>AncientName</placeName></name>
positioned within <div subtype="Book" n="1..9"> / <div subtype="chapter" n="…">.

We walk the tree, and for each place aggregate: canonical ancient name,
coordinates, Getty feature type, mention count, and the set of book.chapter refs.
Output: data/places_raw.json
"""
import json
import re
import pathlib
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "hdt.perseus-eng2.xml"
OUT = ROOT / "data" / "places_raw.json"
NS = {"t": "http://www.tei-c.org/ns/1.0"}

COORD_RE = re.compile(r"\[(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\]")
FEAT_RE = re.compile(r"\]\s*\(([^)]+)\)")


def txt(el):
    return "".join(el.itertext())


def norm_ws(s):
    return " ".join(s.split()) if s else s


def ancient_name(nm):
    """Ancient name = <placeName> text if present, else the <name> element's own
    text (the sibling of <reg>), which is how most mentions are tagged."""
    pn = nm.find("t:placeName", NS)
    if pn is not None:
        return norm_ws(txt(pn))
    parts = [nm.text or ""]
    for child in nm:
        tag = child.tag.split("}")[-1]
        if tag != "reg":
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    return norm_ws("".join(parts)) or None


def main():
    tree = ET.parse(RAW)
    root = tree.getroot()

    # aggregation keyed by place identity (tgn key, else normalised name)
    places = {}

    def rec(key):
        if key not in places:
            places[key] = {
                "key": key, "names": Counter(), "lat": None, "lng": None,
                "feats": Counter(), "kinds": Counter(), "count": 0, "refs": [], "refset": set(),
            }
        return places[key]

    books = root.findall(".//t:div[@subtype='Book']", NS)
    print(f"book divs found: {len(books)}")

    for book in books:
        bn = book.get("n")
        for ch in book.findall(".//t:div[@subtype='chapter']", NS):
            cn = ch.get("n")
            ref = f"{bn}.{cn}"
            for nm in ch.findall(".//t:name", NS):
                typ = nm.get("type")
                if typ not in ("place", "ethnic"):   # ethnic = peoples/tribes
                    continue
                key = nm.get("key") or ""
                ancient = ancient_name(nm)
                reg = nm.find("t:reg", NS)
                regtext = norm_ws(txt(reg)) if reg is not None else ""
                coord = COORD_RE.search(regtext)
                feat = FEAT_RE.search(regtext)
                if not key:
                    # fall back to ancient name as identity so unkeyed still merge
                    key = "name:" + (ancient or regtext or "?").lower()
                r = rec(key)
                r["kinds"][typ] += 1
                if ancient:
                    r["names"][ancient] += 1
                if feat:
                    r["feats"][norm_ws(feat.group(1))] += 1
                if coord and r["lat"] is None:
                    lon = float(coord.group(1)); lat = float(coord.group(2))
                    if abs(lat) <= 90 and abs(lon) <= 180:
                        r["lat"] = lat; r["lng"] = lon
                r["count"] += 1
                if ref not in r["refset"]:
                    r["refset"].add(ref); r["refs"].append(ref)

    # finalise — keep no-coord entries too (lat/lng null) for later geocoding
    out = []
    for r in places.values():
        name = r["names"].most_common(1)[0][0] if r["names"] else None
        if not name:
            continue
        feat = r["feats"].most_common(1)[0][0] if r["feats"] else "Perseus"
        kind = r["kinds"].most_common(1)[0][0] if r["kinds"] else "place"
        out.append({
            "key": r["key"], "name": name, "kind": kind,
            "lat": round(r["lat"], 4) if r["lat"] is not None else None,
            "lng": round(r["lng"], 4) if r["lng"] is not None else None,
            "feat": feat, "mentions": r["count"], "refs": r["refs"],
        })

    out.sort(key=lambda p: -p["mentions"])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    withc = sum(1 for p in out if p["lat"] is not None)
    print(f"total named places: {len(out)}  (with coords: {withc}, no coord: {len(out)-withc})")
    out = [p for p in out if p["lat"] is not None]  # stats below use coord'd only
    print("\nfeature-type distribution:")
    for f, c in Counter(p["feat"] for p in out).most_common():
        print(f"  {c:4d}  {f}")
    print("\ntop 25 by mention count:")
    for p in out[:25]:
        print(f"  {p['mentions']:4d}  {p['name']:22s} ({p['feat']})  [{p['lat']},{p['lng']}]")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
