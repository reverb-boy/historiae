"""Generate + verify a one-line gloss for EVERY annotated name (person, people,
or place) that still lacks one — orphans and blank-resolved alike. Type-aware:
peoples get 'where they lived + role', places get 'what kind + where + role'.

Haiku generates grounded from cited passages; Sonnet fact-checks/fixes. Runs
concurrently, saves incrementally to data/name_glosses.json (resumable).
"""
import json, time, urllib.error, pathlib, unicodedata, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import gloss_lib as G

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "name_glosses.json"
PROG = ROOT / "data" / "name_glosses_progress.txt"
CONC = 10

GEN_SYSTEM = (
    "You are a classical scholar writing ultra-concise glosses for an index to "
    "Herodotus' Histories. Each entry is a PERSON, a PEOPLE/tribe, or a PLACE "
    "(city, region, country, river, lake, island, mountain, or sanctuary); the "
    "TYPE is given. Write ONE sentence identifying it:\n"
    "- PERSON: role or title, origin, and part in the narrative.\n"
    "- PEOPLE: who they are and where they lived, plus their role in the story.\n"
    "- PLACE: what kind of place it is and roughly where, plus why it matters here.\n"
    "Include approximate dates ONLY for well-established historical rulers (e.g. "
    "'r. 570-526 BC'); otherwise omit dates. Ground every claim in the passages or "
    "uncontroversial historical/geographic fact - never speculate or invent. If the "
    "passages say little, keep it minimal (e.g. 'A Libyan tribe of the coast west of "
    "Egypt.'). Output ONLY the gloss sentence: no preamble, no 'X is/was', do not "
    "restart with the name. If the passages genuinely do not identify it at all, "
    "reply with exactly the single word UNKNOWN and nothing else."
)
VER_SYSTEM = (
    "You fact-check one-line glosses for an index to Herodotus' Histories. Given a "
    "name, its TYPE (person/people/place), a proposed gloss, and the source "
    "passages, judge whether the gloss is accurate, supported (by the passages or "
    "uncontroversial history/geography), correctly typed, and concise. Reply with "
    "STRICT JSON only: {\"ok\": true} if fine, or {\"ok\": false, \"fixed\": "
    "\"corrected one-sentence gloss\"} if it has an unsupported claim, wrong fact, "
    "wrong category, or a fabricated/uncertain date. Fixes must be one sentence in "
    "the same terse style, dates only for well-attested rulers."
)
TYPE_LABEL = {"pers": "PERSON", "ethnic": "PEOPLE", "place": "PLACE"}


def gen_user(name, typ, ctx):
    return (f"TYPE: {TYPE_LABEL.get(typ, 'PLACE')}\nName: {name}\n\n"
            f"Passages from Herodotus (book.chapter):\n{ctx or '(no passage text available)'}")


def ver_user(name, typ, gloss, ctx):
    return (f"TYPE: {TYPE_LABEL.get(typ, 'PLACE')}\nName: {name}\nProposed gloss: {gloss}\n\n"
            f"Source passages:\n{ctx or '(none)'}")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def retry(fn, *a, **k):
    for attempt in range(6):
        try:
            return fn(*a, **k)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and attempt < 5:
                time.sleep(2 ** attempt); continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(2 ** attempt); continue
            raise


def main():
    names = json.loads((ROOT / "data" / "all_names.json").read_text(encoding="utf-8"))
    places = G.load_places(); persons = G.load_persons()
    pl_desc = {norm(p["name"]) for p in places if p.get("blurb") or p.get("gloss")}
    pe_desc = {norm(p["name"]) for p in persons if p.get("gloss")}
    text = G.load_text()

    def already(n):
        k = norm(n["name"])
        if n["resolves"] == "place":
            return k in pl_desc
        if n["resolves"] == "person":
            return k in pe_desc
        return False

    todo_all = [n for n in names if not already(n)]
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [n for n in todo_all if n["slug"] not in done]
    ctxs = {n["slug"]: G.context_for(n["refs"], text) for n in todo}
    usage = {"gi": 0, "go": 0, "vi": 0, "vo": 0}

    def process(n):
        ctx = ctxs[n["slug"]]
        gloss, gu = retry(G.messages_call, "claude-haiku-4-5", GEN_SYSTEM,
                          gen_user(n["name"], n["type"], ctx))
        usage["gi"] += gu["input_tokens"]; usage["go"] += gu["output_tokens"]
        if gloss.strip().upper().rstrip(".") == "UNKNOWN":
            return n["slug"], None
        verd, vu = retry(G.messages_call, "claude-sonnet-5", VER_SYSTEM,
                         ver_user(n["name"], n["type"], gloss, ctx), max_tokens=160)
        usage["vi"] += vu["input_tokens"]; usage["vo"] += vu["output_tokens"]
        try:
            v = json.loads(verd)
        except Exception:
            v = {"ok": True}
        final = gloss if v.get("ok", True) else (v.get("fixed") or gloss)
        if final and final.strip().upper().rstrip(".") == "UNKNOWN":
            return n["slug"], None
        return n["slug"], final

    n_done, total, skipped = 0, len(todo), 0
    PROG.write_text(f"starting: {total} to do, {len(done)} already done\n")
    with ThreadPoolExecutor(max_workers=CONC) as ex:
        futs = {ex.submit(process, n): n for n in todo}
        for fut in as_completed(futs):
            nm = futs[fut]
            try:
                slug, gloss = fut.result()
            except Exception as e:
                PROG.write_text(PROG.read_text() + f"ERROR {nm['name']}: {e}\n"); continue
            if gloss:
                done[slug] = gloss
            else:
                skipped += 1
            n_done += 1
            if n_done % 25 == 0 or n_done == total:
                OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0))
                cost = usage["gi"]/1e6 + usage["go"]/1e6*5 + usage["vi"]/1e6*2 + usage["vo"]/1e6*10
                PROG.write_text(f"{n_done}/{total} done ({len(done)} glossed, {skipped} skipped) | "
                                f"~${cost:.2f}\n")
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0))
    cost = usage["gi"]/1e6 + usage["go"]/1e6*5 + usage["vi"]/1e6*2 + usage["vo"]/1e6*10
    PROG.write_text(PROG.read_text() + f"DONE: {len(done)} glosses, {skipped} skipped, ~${cost:.2f}\n")


if __name__ == "__main__":
    main()
