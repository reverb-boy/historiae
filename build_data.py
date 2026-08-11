#!/usr/bin/env python3
"""Normalise the extracted gazetteer into the app's places dataset.

Inputs
  data/places_raw.json       — from extract.py (977 named places; 324 with coords)
  data/places_curated.json   — the 45 hand-authored entries (blurbs + quotes)
  data/raw/tt_places.geojson — ToposText gazetteer (coords, Greek, Pleiades)

Output
  src/data_places.js         — `HERODOTUS.places = [...]` (generated + merged)
"""
import json
import re
import math
import pathlib
import unicodedata
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
RAW = json.loads((ROOT / "data" / "places_raw.json").read_text(encoding="utf-8"))
CUR = json.loads((ROOT / "data" / "places_curated.json").read_text(encoding="utf-8"))
TT = json.loads((ROOT / "data" / "raw" / "tt_places.geojson").read_text(encoding="utf-8"))
OUT = ROOT / "src" / "data_places.js"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"\([^)]*\)", "", s)          # drop qualifiers like "(Egypt)"
    s = re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
    for pre in ("mouths of the ", "mouth of the ", "gulf of ", "lake ", "mount ", "river ", "the "):
        if s.startswith(pre):
            s = s[len(pre):]; break
    return s


def refkey(r):
    a, _, b = r.partition(".")
    return (int(a) if a.isdigit() else 99, int(b) if b.isdigit() else 0)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-") or "place"


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


# ---- ToposText index: normalised name -> list of entries ------------------
tt_index = {}
for f in TT["features"]:
    p = f.get("properties", {})
    g = f.get("geometry") or {}
    coords = g.get("coordinates")
    if not coords or len(coords) < 2:
        continue
    lon, lat = coords[0], coords[1]
    name = p.get("name", "")
    entry = {
        "lat": lat, "lng": lon,
        "greek": p.get("Greek", ""),
        "region": p.get("region", ""),
        "pleiades": (p.get("Pleiades", "") or "").rsplit("/", 1)[-1] if p.get("Pleiades") else "",
        "type": p.get("type", ""),
    }
    tt_index.setdefault(norm(name), []).append(entry)


def tt_lookup(name, lat=None, lng=None):
    """Best ToposText match for a name; if coords given, pick the nearest."""
    cands = tt_index.get(norm(name), [])
    if not cands:
        return None
    if lat is None or len(cands) == 1:
        return cands[0]
    return min(cands, key=lambda e: dist(e["lat"], e["lng"], lat, lng))


# ---- category from Getty/ToposText feature type ---------------------------
def categorize(feat, ttype=""):
    f = (feat + " " + (ttype or "")).lower()
    if any(k in f for k in ("sea", "river", "gulf", "lake", "ocean", "strait", "bay", "spring", "water")):
        return "river"
    if "island" in f:
        return "landmark"
    if "mountain" in f or "cape" in f or "promontory" in f:
        return "landmark"
    if any(k in f for k in ("nation", "region", "department", "governorate", "province", "republic", "territory", "ethnos", "people")):
        return "region"
    return "city"   # inhabited place, deserted settlement, ruins, Perseus, …


def books_from_refs(refs):
    bs = sorted({int(r.split(".")[0]) for r in refs if r and r[0].isdigit()})
    return bs


# ---- rank by mention frequency -> zoom tier -------------------------------
def rank_of(m):
    if m >= 40: return 1
    if m >= 12: return 2
    if m >= 4:  return 3
    return 4
MINZOOM = {1: 3, 2: 5, 3: 6, 4: 7}


# ---- build generated places -----------------------------------------------
places = {}          # id -> place dict
recovered = 0
for r in RAW:
    lat, lng = r["lat"], r["lng"]
    tt = tt_lookup(r["name"], lat, lng)
    if lat is None:
        if tt is None:
            continue                     # can't place it — skip
        lat, lng = round(tt["lat"], 4), round(tt["lng"], 4)
        recovered += 1
    cat = categorize(r["feat"], tt["type"] if tt else "")
    pid = slug(r["name"])
    while pid in places:                 # ensure unique ids
        pid += "-2"
    places[pid] = {
        "id": pid, "name": r["name"], "lat": lat, "lng": lng, "cat": cat,
        "greek": (tt or {}).get("greek", "") or "",
        "region": (tt or {}).get("region", "") or "",
        "pleiades": (tt or {}).get("pleiades", "") or "",
        "mentions": r["mentions"], "refs": r["refs"],
        "books": books_from_refs(r["refs"]),
        "rank": rank_of(r["mentions"]),
    }

# ---- scrub modern / anachronistic names Perseus' Getty geocoding introduced -
# alias: rename to the co-located ancient twin so they merge in dedup below
ALIAS = {"luxor": "Thebes", "karnak": "Thebes", "assuan": "Syene",
         "spain": "Iberia", "gallipoli": "Callipolis"}
# drop: modern cities/countries/infrastructure with no place in Herodotus' world
DROP = {"constantinople", "constantine", "cairo", "gizeh", "fayyum", "assuan dam",
        "suez", "azerbaijan", "beluchistan", "balkan", "crimea", "behistun",
        "barkal", "aras", "pruth", "jerusalem", "rome", "edessa"}
cleaned, dropped_modern = {}, []
for pid, p in places.items():
    k = norm(p["name"])
    if k in DROP:
        dropped_modern.append(p["name"]); continue
    if k in ALIAS:
        p["name"] = ALIAS[k]
    cleaned[pid] = p
places = cleaned

# ---- dedupe near-duplicate generated places (same name, Perseus multi-key) -
from collections import defaultdict
groups = defaultdict(list)
for p in places.values():
    groups[norm(p["name"])].append(p)
deduped = {}
dupes_merged = 0
for nm, grp in groups.items():
    clusters = []
    for p in sorted(grp, key=lambda x: -x["mentions"]):
        for cl in clusters:
            if dist(cl[0]["lat"], cl[0]["lng"], p["lat"], p["lng"]) < 0.2:
                cl.append(p); break
        else:
            clusters.append([p])
    for cl in clusters:
        head = cl[0]                       # most-mentioned wins identity/coords
        for other in cl[1:]:
            dupes_merged += 1
            head["mentions"] += other["mentions"]
            for r in other["refs"]:
                if r not in head["refs"]:
                    head["refs"].append(r)
        head["refs"].sort(key=refkey)
        head["books"] = books_from_refs(head["refs"])
        head["rank"] = rank_of(head["mentions"])
        deduped[head["id"]] = head
places = deduped


# ---- merge the 45 curated entries -----------------------------------------
def find_match(cp):
    n = norm(cp["name"])
    # same-named entries within a generous radius (disambiguates Thebes-Egypt vs
    # -Boeotia by proximity) -> attach to the canonical (most-mentioned) one
    named = [p for p in places.values()
             if norm(p["name"]) == n and dist(p["lat"], p["lng"], cp["lat"], cp["lng"]) < 1.2]
    if named:
        return max(named, key=lambda p: p["mentions"])
    # else only a near-coincident point (different name) counts — kept tight so
    # a curated place can't hijack a distinct neighbour
    close = [p for p in places.values() if dist(p["lat"], p["lng"], cp["lat"], cp["lng"]) < 0.04]
    return min(close, key=lambda p: dist(p["lat"], p["lng"], cp["lat"], cp["lng"])) if close else None

merged = 0
for cp in CUR:
    m = find_match(cp)
    if m:
        merged += 1
        m.update({
            "name": cp["name"], "aka": cp.get("aka", ""), "cat": cp["cat"],
            "region": cp.get("region", m["region"]),
            "blurb": cp["blurb"], "quote": cp.get("quote"),
            "books": sorted(set(m["books"]) | set(cp.get("books", []))),
            "hand": True,
        })
        m["rank"] = min(m["rank"], 2)     # keep pivotal sites visible early
    else:
        pid = slug(cp["name"])
        while pid in places:
            pid += "-c"
        places[pid] = {
            "id": pid, "name": cp["name"], "aka": cp.get("aka", ""),
            "lat": cp["lat"], "lng": cp["lng"], "cat": cp["cat"],
            "region": cp.get("region", ""), "greek": "", "pleiades": "",
            "mentions": 0, "refs": [], "books": cp.get("books", []),
            "blurb": cp["blurb"], "quote": cp.get("quote"), "rank": 2, "hand": True,
        }

# set aka from Greek for generated places lacking one; set minZoom
out = []
for p in places.values():
    if not p.get("aka") and p.get("greek"):
        p["aka"] = p["greek"]
    p["minZoom"] = MINZOOM[p["rank"]]
    p.pop("greek", None)
    if not p.get("pleiades"):
        p.pop("pleiades", None)
    if not p.get("region"):
        p.pop("region", None)
    if not p.get("aka"):
        p.pop("aka", None)
    out.append(p)

out.sort(key=lambda p: (p["rank"], -p["mentions"]))

# ---- emit ------------------------------------------------------------------
header = ("/* GENERATED by build_data.py — do not edit by hand.\n"
          "   Places extracted from the Perseus Godley TEI of Herodotus, geocoded\n"
          "   inline by Perseus + ToposText (CC-BY), ranked by mention frequency,\n"
          "   merged with hand-authored entries. Regenerate: python3 build_data.py */\n")
OUT.write_text(header + "HERODOTUS.places = " +
               json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n",
               encoding="utf-8")

# ---- report ----------------------------------------------------------------
print(f"generated places : {len(out)}  (recovered via ToposText: {recovered}, dupes merged: {dupes_merged}, curated merged: {merged})")
print(f"dropped modern/anachronistic names ({len(dropped_modern)}): {', '.join(sorted(dropped_modern))}")
print("rank distribution:", dict(sorted(Counter(p['rank'] for p in out).items())))
print("category distribution:", dict(Counter(p['cat'] for p in out).most_common()))
print("with blurb (hand):", sum(1 for p in out if p.get('hand')))
print("with aka/Greek   :", sum(1 for p in out if p.get('aka')))
print("with Pleiades id :", sum(1 for p in out if p.get('pleiades')))
print(f"\nwrote {OUT}  ({OUT.stat().st_size//1024} KB)")
print("\nrank-1 (major, zoom 3+):", ", ".join(p['name'] for p in out if p['rank'] == 1))
