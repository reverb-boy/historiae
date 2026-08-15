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
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
RAW = json.loads((ROOT / "data" / "places_raw.json").read_text(encoding="utf-8"))
CUR = json.loads((ROOT / "data" / "places_curated.json").read_text(encoding="utf-8"))
HP = json.loads((ROOT / "data" / "peoples_curated.json").read_text(encoding="utf-8"))
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


def root(s):
    """Bare stem for matching an ethnonym to its place: Athenians/Athens -> athen,
    Persians/Persia -> pers, Thebans/Thebes -> theb."""
    s = norm(s)
    for suf in ("ians", "ans", "enes", "eans", "ines", "ites", "oi", "ae", "es",
                "ia", "is", "us", "os", "um", "on", "a", "e", "i", "s"):
        if s.endswith(suf) and len(s) - len(suf) >= 3:
            return s[:-len(suf)]
    return s


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


# loose index: strip Greek/Latin transliteration + ethnonym endings so that
# "Siphnus"→"Siphnos" and "Paphlagonians"/"Paphlagonia"→same root. Only
# unambiguous loose keys are used, so over-stripping stays safe.
def loose(s):
    return re.sub(r"(ians|ans|enes|eans|ines|oi|ai|ae|es|ia|is|us|os|um|on)$", "", norm(s))

_loose_tmp = {}
for _nn, _entries in tt_index.items():
    _lk = loose(_nn)
    if len(_lk) >= 4:
        _loose_tmp.setdefault(_lk, {})[_nn] = _entries[0]
tt_loose = {lk: next(iter(m.values())) for lk, m in _loose_tmp.items() if len(m) == 1}


def tt_lookup(name, lat=None, lng=None):
    """Best ToposText match for a name; if coords given, pick the nearest.
    Falls back to a unique loose-ending match for spelling variants."""
    cands = tt_index.get(norm(name), [])
    if cands:
        if lat is None or len(cands) == 1:
            return cands[0]
        return min(cands, key=lambda e: dist(e["lat"], e["lng"], lat, lng))
    lk = loose(name)
    if len(lk) >= 4 and lk in tt_loose:
        return tt_loose[lk]
    return None


# ---- Pleiades gazetteer: covers ancient regions & peoples ToposText lacks ---
import gzip, csv
csv.field_size_limit(10 ** 7)
_pl_exact = defaultdict(list)
_pl_loose_names = defaultdict(set)
_pl_loose_coord = {}
with gzip.open(ROOT / "data" / "raw" / "pleiades-places.csv.gz", "rt", encoding="utf-8") as _f:
    for _row in csv.DictReader(_f):
        _t, _la, _lo = _row.get("title", ""), _row.get("reprLat", ""), _row.get("reprLong", "")
        if not (_t and _la and _lo):
            continue
        try:
            _la, _lo = float(_la), float(_lo)
        except ValueError:
            continue
        _ft = (_row.get("featureTypes", "") or "").lower()
        _n = norm(_t)
        if _n:
            _pl_exact[_n].append((_la, _lo, _ft))
        _lk = loose(_t)
        if len(_lk) >= 4:
            _pl_loose_names[_lk].add(_n); _pl_loose_coord[_lk] = (_la, _lo, _ft)


def pleiades_lookup(name):
    """(lat, lng, featureTypes) for a name via Pleiades; unambiguous only."""
    n = norm(name)
    pts = {(a, b) for a, b, _ in _pl_exact.get(n, [])}
    if len(pts) == 1:
        return _pl_exact[n][0]
    lk = loose(name)
    if len(lk) >= 4 and len(_pl_loose_names.get(lk, ())) == 1:
        return _pl_loose_coord[lk]
    return None


# ---- category from Getty/ToposText/Pleiades feature type ------------------
def categorize(feat, ttype="", pl_ft=""):
    f = (feat + " " + (ttype or "") + " " + (pl_ft or "")).lower()
    if any(k in f for k in ("region", "province", "tribe", "ethnos", "people", "nation", "kingdom")):
        return "region"     # areas render as spread labels, not pins
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

# ---- fix individual Perseus mis-geocodes (place, bad≈, good) ---------------
# each: (norm-name, bad_lat, bad_lng, good_lat, good_lng) applied within ~0.3°
COORD_FIX = [
    ("naxos", 32.33, 25.583, 37.104, 25.483),   # Cycladic Naxos dropped into the sea off Libya
]

# regions ToposText resolved to a wrong homonym: force cat=region + correct point
REGION_OVERRIDE = {
    "mysia": (39.5, 28.2),   # the Anatolian region, not the tiny Argolid homonym
}

# ---- coarse parent-area from coordinates (to qualify duplicate names) ------
AREAS = [  # name, lat0, lat1, lng0, lng1
    ("Cyprus", 34.5, 35.8, 32.2, 34.7), ("Sicily", 36.5, 38.4, 12.2, 15.7),
    ("Crete", 34.7, 35.8, 23.3, 26.5), ("the Cyclades", 36.0, 38.0, 24.0, 27.0),
    ("the Dodecanese", 35.8, 37.2, 26.7, 28.7), ("the Peloponnese", 36.3, 38.05, 21.0, 23.2),
    ("Attica", 37.7, 38.3, 23.3, 24.2), ("Boeotia", 38.05, 38.7, 22.7, 23.6),
    ("Thessaly", 38.9, 39.9, 21.5, 23.4), ("Macedonia", 40.0, 41.5, 21.5, 24.5),
    ("the Chersonese", 40.0, 40.75, 26.0, 27.2), ("Thrace", 40.0, 42.5, 24.5, 29.0),
    ("Ionia", 37.5, 39.2, 26.2, 28.2), ("Caria", 36.4, 37.6, 27.0, 29.0),
    ("Egypt", 22.0, 31.7, 24.5, 34.6), ("Libya", 20.0, 33.0, 9.0, 25.5),
    ("Italy", 38.0, 46.0, 7.0, 18.6), ("the Caucasus", 40.5, 43.5, 39.0, 48.0),
    ("Hispania", 36.0, 44.0, -10.0, 3.5), ("Arabia", 22.0, 33.0, 34.0, 40.0),
]
def coarse_area(lat, lng):
    for nm, a, b, c, d in AREAS:
        if a <= lat <= b and c <= lng <= d:
            return nm
    return None


# ---- build generated places -----------------------------------------------
places = {}          # id -> place dict
recovered = recovered_pl = 0
for r in RAW:
    lat, lng = r["lat"], r["lng"]
    tt = tt_lookup(r["name"], lat, lng)
    pl_ft = ""
    if lat is None:
        if tt is not None:
            lat, lng = round(tt["lat"], 4), round(tt["lng"], 4)
            recovered += 1
        else:
            pc = pleiades_lookup(r["name"])     # regions & peoples ToposText lacks
            if pc is None:
                continue                          # can't place it — skip
            lat, lng, pl_ft = round(pc[0], 4), round(pc[1], 4), pc[2]
            recovered_pl += 1
    cat = "people" if r.get("kind") == "ethnic" else categorize(r["feat"], tt["type"] if tt else "", pl_ft)
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

# ---- apply manual coordinate fixes ----------------------------------------
for p in places.values():
    for nm, bla, blo, gla, glo in COORD_FIX:
        if norm(p["name"]) == nm and abs(p["lat"] - bla) < 0.3 and abs(p["lng"] - blo) < 0.3:
            p["lat"], p["lng"] = gla, glo

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

# ---- merge same-root neighbours (Paphlagonia + Paphlagonians, Lesbos + -ians)
# A concrete place (city/island/river) keeps its identity and just absorbs the
# ethnonym's mentions; only pure region+people pairs collapse into an area.
CONCRETE = {"city", "landmark", "river", "sanctuary", "battle", "capital"}
lgroups = defaultdict(list)
for p in places.values():
    lgroups[loose(p["name"])].append(p)
kept = {}
for lk, grp in lgroups.items():
    if len(grp) < 2:
        kept[grp[0]["id"]] = grp[0]; continue
    used = [False] * len(grp)
    for i, p in enumerate(grp):
        if used[i]:
            continue
        cluster = [p]
        for j in range(i + 1, len(grp)):
            if not used[j] and dist(p["lat"], p["lng"], grp[j]["lat"], grp[j]["lng"]) < 0.6:
                used[j] = True; cluster.append(grp[j])
        # head: a concrete place wins; else the shortest name (region over -ians)
        concrete = [c for c in cluster if c["cat"] in CONCRETE]
        head = min(concrete or cluster, key=lambda c: (0 if c["cat"] in CONCRETE else 1, len(c["name"])))
        for o in cluster:
            if o is head:
                continue
            head["mentions"] += o["mentions"]
            for rr in o["refs"]:
                if rr not in head["refs"]:
                    head["refs"].append(rr)
        if head["cat"] in ("region", "people"):     # areas: pick region vs people by form
            head["cat"] = "people" if re.search(r"(ians|ans)$", norm(head["name"])) else "region"
        head["refs"].sort(key=refkey)
        head["books"] = books_from_refs(head["refs"])
        head["rank"] = rank_of(head["mentions"])
        kept[head["id"]] = head
places = kept


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

# ---- qualify duplicate names by parent area (Naxos -> "Naxos (Sicily)") -----
def base_name(n):
    return re.sub(r"\s*\([^)]*\)\s*$", "", n).strip()

by_base = defaultdict(list)
for p in out:
    by_base[norm(base_name(p["name"]))].append(p)
for grp in by_base.values():
    if len(grp) < 2:
        continue
    for p in grp:
        if "(" in p["name"]:
            continue                          # already qualified (e.g. curated)
        area = coarse_area(p["lat"], p["lng"])
        if area:
            p["name"] = base_name(p["name"]) + " (" + area + ")"

# ---- merge places that now share an identical qualified name and sit close --
by_name = defaultdict(list)
for p in out:
    by_name[p["name"]].append(p)
merged_out, same_merged = [], 0
for grp in by_name.values():
    grp.sort(key=lambda x: -(x.get("mentions") or 0))
    used = [False] * len(grp)
    for i, p in enumerate(grp):
        if used[i]:
            continue
        for j in range(i + 1, len(grp)):
            if used[j] or dist(p["lat"], p["lng"], grp[j]["lat"], grp[j]["lng"]) >= 1.2:
                continue
            used[j] = True; same_merged += 1
            o = grp[j]
            p["mentions"] = (p.get("mentions") or 0) + (o.get("mentions") or 0)
            for rr in o.get("refs", []):
                if rr not in p["refs"]:
                    p["refs"].append(rr)
            p["books"] = sorted(set(p.get("books", [])) | set(o.get("books", [])))
            if not p.get("blurb") and o.get("blurb"):
                p.update({"blurb": o["blurb"], "quote": o.get("quote"), "hand": True})
        p["refs"].sort(key=refkey)
        p["rank"] = min(p.get("rank", 4), rank_of(p["mentions"]))
        p["minZoom"] = MINZOOM[p["rank"]]
        merged_out.append(p)
out = merged_out

for p in out:                                    # force known mis-resolved regions
    ov = REGION_OVERRIDE.get(norm(base_name(p["name"])))
    if ov:
        p["lat"], p["lng"], p["cat"] = ov[0], ov[1], "region"

# ---- unify peoples: drop ethnics that duplicate a place/region/hand-people --
# (they were often mis-geocoded, e.g. "Athenians" -> a Pontic homonym), then
# add the 45-style hand-authored peoples so there is ONE peoples category.
covered = set()
for p in out:
    if p["cat"] != "people":
        r = root(p["name"])
        if len(r) >= 3:
            covered.add(r)
for hp in HP:
    r = root(hp["name"])
    if len(r) >= 3:
        covered.add(r)
hand_names = {norm(hp["name"]) for hp in HP}
before = len(out)
out = [p for p in out if p["cat"] != "people"
       or (root(p["name"]) not in covered and norm(p["name"]) not in hand_names)]
dropped_ethnic = before - len(out)
for hp in HP:                                    # hand peoples as area-label entries
    pid = "ppl-" + slug(hp["name"])
    out.append({
        "id": pid, "name": hp["name"], "lat": hp["lat"], "lng": hp["lng"], "cat": "people",
        "blurb": hp["blurb"], "quote": hp.get("quote"), "books": hp.get("books", []),
        "refs": [], "mentions": 50, "rank": 1, "minZoom": 3, "hand": True,
    })

out.sort(key=lambda p: (p["rank"], -p["mentions"]))

# ---- attach place glosses (from ToposText descriptions) --------------------
_gp = ROOT / "data" / "place_glosses.json"
if _gp.exists():
    _gl = json.loads(_gp.read_text(encoding="utf-8"))
    for p in out:
        if not p.get("blurb") and _gl.get(p["id"]):
            p["gloss"] = _gl[p["id"]]
# fallback: fill any still-blank place from the unified name-gloss sweep (by norm name)
_ng = ROOT / "data" / "name_glosses.json"
_an = ROOT / "data" / "all_names.json"
if _ng.exists() and _an.exists():
    _g2 = json.loads(_ng.read_text(encoding="utf-8"))
    _n2g = {norm(r["name"]): _g2[r["slug"]] for r in json.loads(_an.read_text(encoding="utf-8"))
            if _g2.get(r["slug"])}
    for p in out:
        if not p.get("blurb") and not p.get("gloss") and _n2g.get(norm(p["name"])):
            p["gloss"] = _n2g[norm(p["name"])]
print(f"attached {sum(1 for p in out if p.get('gloss'))} place glosses")

# ---- hard overrides for homonym mis-geocodes ------------------------------
# Perseus' Getty geocoding pinned some names to a modern namesake far outside
# Herodotus' world (Oaxus->the Oxus in Tajikistan, Sindi->an Estonian town,
# Nestus->Arabia). Keyed by id so correct homonyms (e.g. Massalia=Marseille)
# are untouched. Coords are the ancient site; cat corrected from the gloss.
# (lat, lng, cat)
HARD_FIXES = {
    "oaxus":      (35.31, 24.84, "city"),      # Axos, Crete
    "nestus":     (40.92, 24.80, "river"),     # Nestos, Thrace (mouth near Abdera)
    "sindi":      (44.90, 37.30, "people"),    # Sindoi, E of the Cimmerian Bosporus
    "assa":       (40.22, 23.92, "city"),      # Assa, Chalkidike (Singitic gulf)
    "carystus":   (38.01, 24.42, "city"),      # Karystos, S. Euboea
    "europus":    (40.92, 22.55, "city"),      # Europos, Macedonia (on the Axios)
    "hellenion":  (30.90, 30.59, "sanctuary"), # the Hellenion at Naucratis, Egypt
    "dolopes":    (39.15, 21.85, "people"),    # Dolopia, Thessaly
    "messapians": (40.35, 18.05, "people"),    # Messapia / Iapygia, SE Italy
    "tauris":     (44.95, 34.10, "landmark"),  # Tauric Chersonese (Crimea)
    "casian":     (31.10, 33.10, "landmark"),  # Mt Casius, Egypt-Syria border
    "issedones":  (48.00, 68.00, "people"),    # inner-Asian steppe beyond Scythia
    "ethiopia":   (19.00, 32.50, "region"),    # Nubia (S. of Egypt), not modern Addis
    # second pass — caught by scan_pins.py (gloss states a region far from the pin)
    "phthia":     (39.15, 22.30, "region"),    # Phthiotis, Thessaly (was S. of Sparta)
    "cius":       (40.42, 29.05, "city"),      # Kios, Mysia on the Propontis (was Danube)
    "arabian-gulf": (25.00, 36.00, "river"),   # the Red Sea (was the Persian Gulf)
    "pedasus":    (37.25, 27.65, "city"),      # Pedasa, Caria (was Messenia)
    "ararus":     (46.00, 27.50, "river"),     # Scythian river of the Ister (was the Saone)
    "naparis":    (45.50, 28.00, "river"),     # Scythian tributary of the Ister (was Hungary)
    "chalybes":   (40.80, 38.50, "people"),    # Pontic Anatolia (was Lebanon)
    "crobyzi":    (45.00, 28.00, "people"),    # Thracians N. of the Danube (was Ukraine)
    "psylli":     (30.50, 18.50, "people"),    # Libyan people of the Syrtis (was the Bosphorus)
    "smila":      (40.50, 23.00, "city"),      # Crossaea, on the Thermaic gulf (was Ukraine)
    "olbia":      (46.63, 31.90, "city"),      # Greek colony on the N. Black Sea (was Bithynia)
    "aphrodisias": (32.90, 21.00, "landmark"), # island off Cyrene, Libya (was Bithynia)
    "soloeis":    (32.50, -9.30, "landmark"),  # NW-African cape (was Sicily)
    "nysa":       (18.50, 33.00, "landmark"),  # mythical Nysa beyond Egypt (was Anatolia)
    # third pass — region/people area-labels floating off their territory
    # (screened against the scan_pins.py gazetteer boxes)
    "attica":      (38.00, 23.80, "region"),   # over Athens (was up in the Euboean gulf)
    "hyrcanians":  (37.00, 54.00, "people"),   # SE Caspian (was in Lydia)
    "theraeans":   (36.42, 25.43, "people"),   # Thera/Santorini (was off Caria)
    "bithynians":  (40.50, 30.30, "people"),   # NW Anatolia (was in the Black Sea)
    "paphlagonia": (41.40, 34.00, "region"),   # N. Anatolian coast (was in the sea)
    "pamphylians": (37.00, 31.00, "people"),   # S. Anatolian coast
    "phrygia":     (39.00, 31.00, "region"),   # inland W-central Anatolia
    "bactria":     (36.70, 66.90, "region"),   # Bactria proper (was S. Afghanistan)
    "india":       (28.00, 71.00, "region"),   # the Indus (was the Deccan)
}
# entries that are not places at all (persons the TEI mistagged) or duplicates
DROP_IDS = {
    "cos-2",       # spurious Getty homonym duplicating the real Aegean Cos
    "solois",      # duplicate of "soloeis" (same NW-African cape)
    "melissa",     # person: wife of Periander, tyrant of Corinth
    "olen",        # the gloss itself says "a man, not a place"
    "menelaus",    # person: king of Sparta, husband of Helen
}
_fixed = 0
for p in out:
    h = HARD_FIXES.get(p["id"])
    if h:
        p["lat"], p["lng"], p["cat"] = h[0], h[1], h[2]
        _fixed += 1
out = [p for p in out if p["id"] not in DROP_IDS]
print(f"applied {_fixed}/{len(HARD_FIXES)} hard geocode fixes, dropped {len(DROP_IDS)} non-places/dupes")

# ---- emit ------------------------------------------------------------------
header = ("/* GENERATED by build_data.py — do not edit by hand.\n"
          "   Places extracted from the Perseus Godley TEI of Herodotus, geocoded\n"
          "   inline by Perseus + ToposText (CC-BY), ranked by mention frequency,\n"
          "   merged with hand-authored entries. Regenerate: python3 build_data.py */\n")
OUT.write_text(header + "HERODOTUS.places = " +
               json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n",
               encoding="utf-8")

# ---- report ----------------------------------------------------------------
print(f"generated places : {len(out)}  (recovered ToposText: {recovered}, Pleiades: {recovered_pl}, dupes merged: {dupes_merged}, curated merged: {merged})")
print(f"dropped modern/anachronistic names ({len(dropped_modern)}): {', '.join(sorted(dropped_modern))}")
print("rank distribution:", dict(sorted(Counter(p['rank'] for p in out).items())))
print("category distribution:", dict(Counter(p['cat'] for p in out).most_common()))
print("with blurb (hand):", sum(1 for p in out if p.get('hand')))
print("with aka/Greek   :", sum(1 for p in out if p.get('aka')))
print("with Pleiades id :", sum(1 for p in out if p.get('pleiades')))
print(f"\nwrote {OUT}  ({OUT.stat().st_size//1024} KB)")
print("\nrank-1 (major, zoom 3+):", ", ".join(p['name'] for p in out if p['rank'] == 1))
