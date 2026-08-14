#!/usr/bin/env python3
"""Extract the readable Godley text + person names from the Perseus TEI.

Perseus interleaves geo-annotations into the prose (<reg>Bodrum [27.4,37.5]…</reg>);
we strip those (and <note>s) to recover clean reading text, chapter by chapter.
We also collect every person name (<name type="pers">) with its book.chapter refs.

Outputs
  src/data_text.js     HERODOTUS_TEXT = { "1": [[chapter, text], …], … }
  src/data_persons.js  HERODOTUS.persons = [{ id, name, mentions, refs[] }, …]
"""
import json
import re
import pathlib
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "hdt.perseus-eng2.xml"
NS = {"t": "http://www.tei-c.org/ns/1.0"}
SKIP = {"reg", "note"}   # drop the modern geo-annotation + editorial notes


def esc_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def name_text(nm):
    """Display text of a <name> element, excluding its <reg> geo-annotation."""
    parts = [nm.text or ""]
    for child in nm:
        if child.tag.split("}")[-1] != "reg":
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    return " ".join("".join(parts).split())


def clean_html(el):
    """Readable HTML of a chapter: text HTML-escaped, every place/people/person
    name wrapped in <n> (so the reader can turn it into a search link); the
    <reg>/<note> subtrees are dropped."""
    out = []

    def rec(e):
        tag = e.tag.split("}")[-1]
        if tag in SKIP:
            if e.tail:
                out.append(esc_html(e.tail))
            return
        if tag == "name" and e.get("type") in ("place", "ethnic", "pers"):
            disp = name_text(e)
            if disp:
                out.append("<n>" + esc_html(disp) + "</n>")
            if e.tail:
                out.append(esc_html(e.tail))
            return
        if e.text:
            out.append(esc_html(e.text))
        for c in e:
            rec(c)
        if e.tail:
            out.append(esc_html(e.tail))

    if el.text:
        out.append(esc_html(el.text))
    for c in el:
        rec(c)
    s = " ".join("".join(out).split())          # collapse whitespace (tags have none)
    s = re.sub(r"\s+([,.;:!?’”)])", r"\1", s)    # no space before punctuation
    s = re.sub(r"([“‘(])\s+", r"\1", s)           # no space after opening bracket/quote
    return s


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-") or "x"


def main():
    root = ET.parse(RAW).getroot()
    books = root.findall(".//t:div[@subtype='Book']", NS)

    text = {}
    persons = {}   # norm-name -> {names: Counter, refs: [], refset: set}
    total_words = 0

    for book in books:
        bn = book.get("n")
        chapters = []
        for ch in book.findall(".//t:div[@subtype='chapter']", NS):
            cn = ch.get("n")
            body = clean_html(ch)
            total_words += len(body.split())
            chapters.append([cn, body])
            ref = f"{bn}.{cn}"
            for nm in ch.findall(".//t:name[@type='pers']", NS):
                name = name_text(nm)
                if not name or len(name) < 2:
                    continue
                key = norm(name)
                if not key:
                    continue
                p = persons.setdefault(key, {"names": Counter(), "refs": [], "refset": set()})
                p["names"][name] += 1
                if ref not in p["refset"]:
                    p["refset"].add(ref); p["refs"].append(ref)
        text[bn] = chapters

    # persons -> list
    plist = []
    for key, p in persons.items():
        name = p["names"].most_common(1)[0][0]
        plist.append({
            "id": "per-" + slug(name), "name": name,
            "mentions": sum(p["names"].values()), "refs": p["refs"],
        })
    plist.sort(key=lambda x: -x["mentions"])
    # de-dupe ids
    seen = set()
    for p in plist:
        pid = p["id"]
        while pid in seen:
            pid += "-2"
        p["id"] = pid; seen.add(pid)

    gp = ROOT / "data" / "person_glosses.json"        # attach generated glosses
    if gp.exists():
        gl = json.loads(gp.read_text(encoding="utf-8"))
        for p in plist:
            if gl.get(p["id"]):
                p["gloss"] = gl[p["id"]]
    # fallback: fill any still-blank person from the unified name-gloss sweep (by norm name)
    ng = ROOT / "data" / "name_glosses.json"
    an = ROOT / "data" / "all_names.json"
    if ng.exists() and an.exists():
        gl2 = json.loads(ng.read_text(encoding="utf-8"))
        norm2gloss = {norm(r["name"]): gl2[r["slug"]] for r in json.loads(an.read_text(encoding="utf-8"))
                      if gl2.get(r["slug"])}
        for p in plist:
            if not p.get("gloss") and norm2gloss.get(norm(p["name"])):
                p["gloss"] = norm2gloss[norm(p["name"])]
    print(f"attached {sum(1 for p in plist if p.get('gloss'))} person glosses")

    (ROOT / "src" / "data_text.js").write_text(
        "HERODOTUS_TEXT = " + json.dumps(text, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    (ROOT / "src" / "data_persons.js").write_text(
        "HERODOTUS.persons = " + json.dumps(plist, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")

    tk = (ROOT / "src" / "data_text.js").stat().st_size // 1024
    pk = (ROOT / "src" / "data_persons.js").stat().st_size // 1024
    print(f"text   : {len(text)} books, {sum(len(v) for v in text.values())} chapters, "
          f"~{total_words} words -> data_text.js ({tk} KB)")
    print(f"persons: {len(plist)} distinct -> data_persons.js ({pk} KB)")
    print("top persons:", ", ".join(f"{p['name']}({p['mentions']})" for p in plist[:12]))
    print("sample 1.1:", text["1"][0][1][:160])


if __name__ == "__main__":
    main()
