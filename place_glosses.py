"""Attach a factual gloss to each place from the ToposText description field
(free — no API). Matches by normalised base name + nearest coordinates.
Writes data/place_glosses.json {id: gloss}.
"""
import json, re, math, unicodedata, pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
    for pre in ("mouths of the ", "mouth of the ", "gulf of ", "lake ", "mount ", "river ", "the "):
        if s.startswith(pre):
            s = s[len(pre):]; break
    return s


def clean_desc(d):
    d = d.strip()
    # drop a leading Greek-script token + separator: "Θῆβαι - Thebes, ..." -> "Thebes, ..."
    d = re.sub(r"^[^\x00-\x7f][^-–]*[-–]\s*", "", d)
    d = re.sub(r"^[-–—]\s*", "", d).strip()          # stray leading dash
    d = re.sub(r"\s+", " ", d).strip()
    if d and d[-1] not in ".!?":
        d += "."
    return d


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


places = json.loads((ROOT / "src" / "data_places.js").read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";\n"))
tt = json.loads((ROOT / "data" / "raw" / "tt_places.geojson").read_text(encoding="utf-8"))

idx = {}
for f in tt["features"]:
    p = f.get("properties", {}); g = f.get("geometry") or {}
    desc = p.get("description", "")
    coords = g.get("coordinates")
    if not desc or not coords or len(coords) < 2:
        continue
    idx.setdefault(norm(p.get("name", "")), []).append((coords[1], coords[0], desc))

base = lambda n: re.sub(r"\s*\([^)]*\)\s*$", "", n)
out = {}
for pl in places:
    if pl.get("blurb"):
        continue
    cands = idx.get(norm(base(pl["name"])), [])
    if not cands:
        continue
    best = min(cands, key=lambda e: dist(e[0], e[1], pl["lat"], pl["lng"]))
    if dist(best[0], best[1], pl["lat"], pl["lng"]) > 1.0:
        continue
    gl = clean_desc(best[2])
    if len(gl) > 8:
        out[pl["id"]] = gl

(ROOT / "data" / "place_glosses.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"place glosses: {len(out)} / {sum(1 for p in places if not p.get('blurb'))} un-blurbed places")
for pid in list(out)[:6]:
    print(" ", pid, "->", out[pid][:80])
