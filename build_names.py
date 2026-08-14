"""Emit src/data_names.js — the orphan names (peoples/tribes and minor
places/rivers that are name-linked in the reader but have no mapped place or
listed person). Each becomes a searchable, un-pinned card carrying its gloss,
type, and 'Mentioned at' refs. Glosses come from data/name_glosses.json (slug).
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    names = json.loads((ROOT / "data" / "all_names.json").read_text(encoding="utf-8"))
    gp = ROOT / "data" / "name_glosses.json"
    gl = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else {}

    out = []
    for n in names:
        if n["resolves"] != "orphan":
            continue
        out.append({
            "id": "nam-" + n["slug"],
            "name": n["name"],
            "type": n["type"],            # ethnic | place
            "gloss": gl.get(n["slug"], ""),
            "refs": n["refs"],
            "mentions": n["mentions"],
        })
    out.sort(key=lambda x: -x["mentions"])

    (ROOT / "src" / "data_names.js").write_text(
        "HERODOTUS.names = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    glossed = sum(1 for o in out if o["gloss"])
    print(f"data_names.js: {len(out)} orphan names ({glossed} glossed, {len(out)-glossed} without)")


if __name__ == "__main__":
    main()
