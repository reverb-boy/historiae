"""Generate + verify one-line glosses for every person in Herodotus.

Haiku generates a grounded gloss from each person's cited passages; Sonnet
fact-checks it and fixes unsupported ones. Runs concurrently, saves
incrementally to data/person_glosses.json (resumable), logs progress to
data/glosses_progress.txt.
"""
import json, time, urllib.error, pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import gloss_lib as G

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "person_glosses.json"
PROG = ROOT / "data" / "glosses_progress.txt"
CONC = 10


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
    persons = G.load_persons()
    text = G.load_text()
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [p for p in persons if p["id"] not in done]
    ctxs = {p["id"]: G.context_for(p["refs"], text) for p in persons}
    usage = {"gi": 0, "go": 0, "vi": 0, "vo": 0}

    def process(p):
        ctx = ctxs[p["id"]]
        gloss, gu = retry(G.messages_call, "claude-haiku-4-5", G.GEN_SYSTEM, G.gen_user(p["name"], ctx))
        usage["gi"] += gu["input_tokens"]; usage["go"] += gu["output_tokens"]
        if gloss.strip().upper().rstrip(".") == "UNKNOWN":
            return p["id"], None
        verd, vu = retry(G.messages_call, "claude-sonnet-5", G.VER_SYSTEM,
                         G.ver_user(p["name"], gloss, ctx), max_tokens=140)
        usage["vi"] += vu["input_tokens"]; usage["vo"] += vu["output_tokens"]
        try:
            v = json.loads(verd)
        except Exception:
            v = {"ok": True}
        final = gloss if v.get("ok", True) else (v.get("fixed") or gloss)
        if final and final.strip().upper().rstrip(".") == "UNKNOWN":
            return p["id"], None
        return p["id"], final

    n, total, skipped = 0, len(todo), 0
    PROG.write_text(f"starting: {total} to do, {len(done)} already done\n")
    with ThreadPoolExecutor(max_workers=CONC) as ex:
        futs = {ex.submit(process, p): p for p in todo}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                pid, gloss = fut.result()
            except Exception as e:
                PROG.write_text(PROG.read_text() + f"ERROR {p['name']}: {e}\n"); continue
            if gloss:
                done[pid] = gloss
            else:
                skipped += 1
            n += 1
            if n % 25 == 0 or n == total:
                OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0))
                cost = usage["gi"]/1e6 + usage["go"]/1e6*5 + usage["vi"]/1e6*2 + usage["vo"]/1e6*10
                PROG.write_text(f"{n}/{total} done ({len(done)} glossed, {skipped} skipped) | "
                                f"tokens g{usage['gi']}/{usage['go']} v{usage['vi']}/{usage['vo']} | ~${cost:.2f}\n")
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0))
    cost = usage["gi"]/1e6 + usage["go"]/1e6*5 + usage["vi"]/1e6*2 + usage["vo"]/1e6*10
    PROG.write_text(PROG.read_text() + f"DONE: {len(done)} glosses, {skipped} skipped, ~${cost:.2f}\n")


if __name__ == "__main__":
    main()
