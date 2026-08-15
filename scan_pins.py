"""QA: sanity-check every place pin against the geography stated in its own
(verified) gloss. Two independent checks:

1) GEO  — the gloss names a region ("a city in Mysia") and/or nearby places
          ("near Abdera"); if the pin sits far from ALL of those anchors it is
          very likely a homonym mis-geocode. Regions carry a meta-region
          (Mysia -> Asia Minor -> Asia) so the report reads hierarchically.
2) PERSON — the gloss describes a person ("wife of X", "son of Y") with no
          place-type word: the entry is a person mistagged as a place.

Prints candidates ranked by mentions; it does NOT edit data (feeds HARD_FIXES).
"""
import json, re, math, unicodedata, pathlib
ROOT = pathlib.Path(__file__).resolve().parent


def load(p): s = open(p, encoding="utf-8").read(); return json.loads(s.split("=", 1)[1].strip().rstrip(";\n"))


# region -> (lat0, lat1, lng0, lng1, meta-region)
REG = {
 "thessaly": (39, 40, 21.3, 23.5, "Greece"), "phthiotis": (38.8, 39.4, 22, 23, "Greece"),
 "phthia": (38.8, 39.4, 22, 23, "Greece"), "boeotia": (38, 38.6, 22.5, 23.8, "Greece"),
 "attica": (37.6, 38.2, 23.3, 24.1, "Greece"), "corinth": (37.7, 38.1, 22.6, 23.1, "Greece"),
 "argolis": (37.3, 37.8, 22.6, 23.4, "Greece"), "argos": (37.3, 37.8, 22.6, 23.4, "Greece"),
 "laconia": (36.7, 37.3, 22, 22.9, "Greece"), "sparta": (36.9, 37.2, 22.3, 22.6, "Greece"),
 "messenia": (36.8, 37.4, 21.6, 22.3, "Greece"), "elis": (37.5, 38, 21.2, 21.8, "Greece"),
 "achaea": (37.9, 38.3, 21.6, 22.5, "Greece"), "arcadia": (37.3, 37.9, 21.9, 22.5, "Greece"),
 "aetolia": (38.3, 38.9, 21.3, 22.1, "Greece"), "acarnania": (38.5, 39, 20.8, 21.4, "Greece"),
 "locris": (38.4, 38.9, 22.4, 23.3, "Greece"), "phocis": (38.4, 38.8, 22.2, 22.8, "Greece"),
 "delphi": (38.4, 38.6, 22.4, 22.6, "Greece"), "thesprotia": (39, 40, 20, 21, "Greece"),
 "epirus": (39, 40.3, 20, 21.5, "Greece"), "macedonia": (40, 41.3, 21.5, 24, "Greece"),
 "thrace": (40.7, 42.5, 23.4, 29, "Thrace"), "chalcidice": (39.9, 40.5, 23, 24.2, "Greece"),
 "pieria": (40, 40.5, 22, 22.6, "Greece"), "thessalian": (39, 40, 21.3, 23.5, "Greece"),
 "boeotian": (38, 38.6, 22.5, 23.8, "Greece"), "thracian": (40.7, 42.5, 23.4, 29, "Thrace"),
 "macedonian": (40, 41.3, 21.5, 24, "Greece"), "arcadian": (37.3, 37.9, 21.9, 22.5, "Greece"),
 "euboea": (38, 39, 23, 24.5, "Greece"), "euboean": (38, 39, 23, 24.5, "Greece"),
 "crete": (34.8, 35.8, 23.4, 26.4, "Crete"), "cretan": (34.8, 35.8, 23.4, 26.4, "Crete"),
 "cyclades": (36.5, 37.9, 24, 26, "Aegean"), "rhodes": (35.9, 36.5, 27.7, 28.4, "Aegean"),
 "cyprus": (34.5, 35.7, 32.2, 34.7, "Cyprus"), "cyprian": (34.5, 35.7, 32.2, 34.7, "Cyprus"),
 "lesbos": (38.9, 39.4, 25.8, 26.6, "Aegean"), "samos": (37.6, 37.9, 26.6, 27.1, "Aegean"),
 "corcyra": (39.4, 39.8, 19.8, 20.2, "Greece"), "salamis": (37.9, 38, 23.4, 23.6, "Greece"),
 "ionia": (37.3, 38.7, 26.3, 27.6, "Asia Minor"), "ionian": (37.3, 38.7, 26.3, 27.6, "Asia Minor"),
 "aeolia": (38.7, 39.6, 26.2, 27.2, "Asia Minor"), "aeolis": (38.7, 39.6, 26.2, 27.2, "Asia Minor"),
 "caria": (36.6, 37.6, 27, 29, "Asia Minor"), "carian": (36.6, 37.6, 27, 29, "Asia Minor"),
 "lydia": (38, 39.3, 27.3, 29.5, "Asia Minor"), "lydian": (38, 39.3, 27.3, 29.5, "Asia Minor"),
 "mysia": (39.3, 40.6, 26.8, 29.5, "Asia Minor"), "mysian": (39.3, 40.6, 26.8, 29.5, "Asia Minor"),
 "phrygia": (38.5, 40, 29.5, 32.5, "Asia Minor"), "phrygian": (38.5, 40, 29.5, 32.5, "Asia Minor"),
 "lycia": (36, 36.7, 29, 30.5, "Asia Minor"), "lycian": (36, 36.7, 29, 30.5, "Asia Minor"),
 "pamphylia": (36.7, 37.2, 30.5, 32, "Asia Minor"), "cilicia": (36.5, 37.5, 32.5, 36.5, "Asia Minor"),
 "cilician": (36.5, 37.5, 32.5, 36.5, "Asia Minor"), "cappadocia": (38, 40, 34, 37.5, "Asia Minor"),
 "paphlagonia": (41, 41.9, 32.5, 35.5, "Asia Minor"), "bithynia": (40, 41, 29, 31.5, "Asia Minor"),
 "troad": (39.5, 40.1, 26, 26.7, "Asia Minor"), "propontis": (40.3, 41.1, 27, 29.5, "Asia Minor"),
 "hellespont": (40, 40.5, 26.1, 26.7, "Asia Minor"), "asia minor": (36, 41.5, 26, 37, "Asia Minor"),
 "anatolia": (36, 41.5, 26, 37, "Asia Minor"),
 "phoenicia": (33, 35, 35, 36.3, "Levant"), "phoenician": (33, 35, 35, 36.3, "Levant"),
 "syria": (34, 37, 36, 39, "Levant"), "syrian": (34, 37, 36, 39, "Levant"),
 "palestine": (31, 33, 34.2, 35.5, "Levant"), "assyria": (34, 37, 41, 44, "Mesopotamia"),
 "assyrian": (34, 37, 41, 44, "Mesopotamia"), "babylon": (30, 34, 43, 46, "Mesopotamia"),
 "babylonia": (30, 34, 43, 46, "Mesopotamia"), "mesopotamia": (31, 36, 40, 46, "Mesopotamia"),
 "media": (34, 38, 45, 52, "Iran"), "median": (34, 38, 45, 52, "Iran"),
 "persia": (27, 32, 50, 55, "Iran"), "persis": (27, 32, 50, 55, "Iran"),
 "armenia": (38, 41, 40, 45, "Caucasus"), "colchis": (41.5, 43, 40, 43, "Caucasus"),
 "parthia": (35, 38, 54, 58, "Iran"), "hyrcania": (36, 38, 53, 56, "Iran"),
 "bactria": (36, 38, 64, 69, "Central Asia"), "sogdiana": (38, 40, 64, 68, "Central Asia"),
 "india": (24, 33, 66, 77, "India"), "indian": (24, 33, 66, 77, "India"),
 "scythia": (44, 52, 28, 50, "Scythia"), "scythian": (44, 52, 28, 50, "Scythia"),
 "sarmatia": (46, 52, 40, 55, "Scythia"), "maeotis": (45, 47.5, 35, 39, "Scythia"),
 "tauris": (44.5, 46, 33, 36, "Scythia"), "crimea": (44.5, 46, 33, 36, "Scythia"),
 "egypt": (22, 31.5, 25, 34, "Egypt"), "egyptian": (22, 31.5, 25, 34, "Egypt"),
 "nubia": (17, 23, 30, 35, "Nubia"), "ethiopia": (16, 23, 30, 36, "Nubia"),
 "ethiopian": (16, 23, 30, 36, "Nubia"), "libya": (23, 33, 10, 25, "Libya"),
 "libyan": (23, 33, 10, 25, "Libya"), "cyrenaica": (30, 33, 19, 25, "Libya"),
 "cyrene": (32, 33, 21, 22.5, "Libya"),
 "italy": (38, 45, 7, 18, "Italy"), "italian": (38, 45, 7, 18, "Italy"),
 "sicily": (36.5, 38.3, 12, 15.7, "Sicily"), "sicilian": (36.5, 38.3, 12, 15.7, "Sicily"),
 "iapygia": (39.8, 40.6, 17.5, 18.6, "Italy"), "messapia": (39.8, 40.6, 17.5, 18.6, "Italy"),
 "etruria": (42, 43.5, 10.5, 12.3, "Italy"), "iberia": (36, 43, -9, 3, "Iberia"),
 "spain": (36, 43, -9, 3, "Iberia"), "sardinia": (39, 41, 8, 10, "Italy"),
 "peloponnese": (36.5, 38.2, 21, 23.4, "Greece"), "hellas": (36, 40.5, 20, 26.5, "Greece"),
 "greece": (36, 40.5, 20, 26.5, "Greece"), "aegean": (36, 40, 23, 27.5, "Aegean"),
}
META = {  # coarse meta-region boxes, used as a lenient fallback anchor
 "asia minor": (36, 41.5, 26, 37), "asia": (26, 44, 40, 80), "europe": (37, 52, -6, 40),
 "africa": (15, 34, -8, 34), "greece": (36, 40.5, 20, 26.5), "levant": (31, 37, 34, 39),
}
PERSON_PAT = re.compile(r"\b(son|daughter|wife|husband|father|mother|brother|sister|king|queen|"
                        r"tyrant|general|commander|satrap|admiral|priest|priestess|noble|"
                        r"prince|princess|concubine|envoy|seer) of\b", re.I)
PLACE_WORD = re.compile(r"\b(city|town|polis|village|region|district|country|island|river|lake|"
                        r"gulf|sea|strait|spring|mountain|mount|promontory|cape|peninsula|"
                        r"harbou?r|port|plain|sanctuary|temple|oracle|people|tribe|nation|"
                        r"colony|settlement|fort|coast)\b", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def outdist(la, lo, b):
    dla = max(b[0] - la, la - b[1], 0); dlo = max(b[2] - lo, lo - b[3], 0)
    return math.hypot(dla, dlo)


def meta_of(la, lo):
    for m, b in META.items():
        if b[0] <= la <= b[1] and b[2] <= lo <= b[3]:
            return m
    return "??"


def main():
    places = load(ROOT / "src" / "data_places.js")
    coords = {}                                   # name(lower) -> (lat,lng) for gloss place-refs
    for p in places:
        coords.setdefault(p["name"].lower(), (p["lat"], p["lng"]))
    MARGIN = 2.5
    geo, per = [], []
    for p in places:
        g = p.get("gloss") or p.get("blurb") or ""
        if not g:
            continue
        gl = g.lower()
        la, lo = p["lat"], p["lng"]
        # person check
        if PERSON_PAT.search(g) and not PLACE_WORD.search(g):
            per.append((p["mentions"], p["name"], p["cat"], round(la, 1), round(lo, 1), g[:75]))
        # anchors: region words, meta words, and other place names in the gloss
        anchors = []                              # (label, out-distance)
        stated = []
        for k, b in REG.items():
            if re.search(r"\b" + re.escape(k) + r"\b", gl):
                anchors.append(outdist(la, lo, b)); stated.append((k, b[4]))
        for k, b in META.items():
            if re.search(r"\b" + re.escape(k) + r"\b", gl):
                anchors.append(outdist(la, lo, (b[0], b[1], b[2], b[3])))
        self_l = p["name"].lower()
        for m in re.findall(r"\b([A-Z][a-z]{4,})\b", g):    # capitalised place-ref in gloss
            ml = m.lower()
            if ml != self_l and ml in coords:
                cx = coords[ml]; anchors.append(math.hypot(la - cx[0], lo - cx[1]))
        if not anchors:
            continue
        near = min(anchors)
        if near > MARGIN and stated:
            reg_lbl = ", ".join(f"{k}({mr})" for k, mr in stated[:3])
            geo.append((round(near, 1), p["mentions"], p["name"], p["cat"],
                        round(la, 1), round(lo, 1), meta_of(la, lo), reg_lbl, g[:60]))

    print(f"=== GEO: pin far ({MARGIN}deg+) from every region/place its gloss names ({len(geo)}) ===")
    for f in sorted(geo, key=lambda x: -x[0]):
        print(f"  off{f[0]:5}  {f[2]:24} cat={f[3]:8} at({f[4]},{f[5]})->[{f[6]}]  says: {f[7]}")
    print(f"\n=== PERSON: gloss describes a person, no place-word ({len(per)}) ===")
    for f in sorted(per, key=lambda x: -x[0]):
        print(f"  m{f[0]:<3} {f[1]:22} cat={f[2]:8} at({f[3]},{f[4]})  \"{f[5]}...\"")


if __name__ == "__main__":
    main()
