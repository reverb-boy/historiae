#!/usr/bin/env python3
"""Collect EVERY annotated name in the TEI (place / ethnic / pers) with its type
and book.chapter refs, and record whether it already resolves to a mapped place
or a listed person — or is an orphan (a name-link in the reader that currently
leads nowhere, e.g. minor tribes and rivers). Feeds the gloss pipeline + wiring.

Output  data/all_names.json = [
  { slug, name, type: place|ethnic|pers, refs:[...], mentions, resolves: place|person|orphan },
  ...]
"""
import json, re, pathlib, unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "hdt.perseus-eng2.xml"
NS = {"t": "http://www.tei-c.org/ns/1.0"}


def name_text(nm):
    parts = [nm.text or ""]
    for child in nm:
        if child.tag.split("}")[-1] != "reg":
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    return " ".join("".join(parts).split())


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-") or "x"


def load_js(path):
    return json.loads(path.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";\n"))


def main():
    root = ET.parse(RAW).getroot()
    # norm -> {names: Counter, types: Counter, refs: [], refset: set}
    names = {}
    for book in root.findall(".//t:div[@subtype='Book']", NS):
        bn = book.get("n")
        for ch in book.findall(".//t:div[@subtype='chapter']", NS):
            ref = f"{bn}.{ch.get('n')}"
            for nm in ch.findall(".//t:name", NS):
                typ = nm.get("type")
                if typ not in ("place", "ethnic", "pers"):
                    continue
                disp = name_text(nm)
                if not disp or len(disp) < 2:
                    continue
                key = norm(disp)
                if not key:
                    continue
                d = names.setdefault(key, {"names": Counter(), "types": Counter(),
                                           "refs": [], "refset": set()})
                d["names"][disp] += 1
                d["types"][typ] += 1
                if ref not in d["refset"]:
                    d["refset"].add(ref); d["refs"].append(ref)

    places = load_js(ROOT / "src" / "data_places.js")
    persons = load_js(ROOT / "src" / "data_persons.js")
    place_norm = {norm(p["name"]) for p in places}
    person_norm = {norm(p["name"]) for p in persons}

    out = []
    for key, d in names.items():
        disp = d["names"].most_common(1)[0][0]
        typ = d["types"].most_common(1)[0][0]
        if key in place_norm:
            resolves = "place"
        elif key in person_norm:
            resolves = "person"
        else:
            resolves = "orphan"
        out.append({
            "slug": slug(disp), "name": disp, "type": typ,
            "refs": d["refs"], "mentions": sum(d["names"].values()),
            "resolves": resolves,
        })
    out.sort(key=lambda x: -x["mentions"])
    # de-dupe slugs
    seen = set()
    for r in out:
        s = r["slug"]
        while s in seen:
            s += "-2"
        r["slug"] = s; seen.add(s)

    (ROOT / "data" / "all_names.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")

    byres = Counter(r["resolves"] for r in out)
    bytyp = Counter(r["type"] for r in out)
    print(f"all names: {len(out)}  resolves={dict(byres)}  types={dict(bytyp)}")
    orphans = [r for r in out if r["resolves"] == "orphan"]
    print(f"orphans: {len(orphans)}  (types={dict(Counter(r['type'] for r in orphans))})")
    print("sample orphans:", ", ".join(f"{r['name']}[{r['type']}]" for r in orphans[:12]))


if __name__ == "__main__":
    main()
