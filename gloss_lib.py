"""Shared helpers for generating grounded one-line glosses of Herodotus names.

Loads the generated data, assembles each entity's cited passages (plain text,
capped), and provides a raw-HTTPS Messages/Batch API caller (no SDK needed).
"""
import json, os, re, html, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
KEY = open(os.path.expanduser("~/.hist_anthropic_key")).read().strip()
API = "https://api.anthropic.com/v1"
HEADERS = {"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}


def _load_js_assign(path):
    """Parse a `NAME = <json>;` file into the JSON value."""
    txt = path.read_text(encoding="utf-8")
    txt = txt.split("=", 1)[1].strip()
    if txt.endswith(";"):
        txt = txt[:-1]
    return json.loads(txt)


def load_persons():
    return _load_js_assign(ROOT / "src" / "data_persons.js")


def load_places():
    return json.loads((ROOT / "src" / "data_places.js").read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";\n"))


def load_text():
    data = _load_js_assign(ROOT / "src" / "data_text.js")   # {book: [[chap, html], ...]}
    by_ref = {}
    for bn, chapters in data.items():
        for cn, htmltext in chapters:
            plain = re.sub(r"</?n>", "", htmltext)          # drop the <n> name tags
            by_ref[f"{bn}.{cn}"] = html.unescape(plain)
    return by_ref


def context_for(refs, text_by_ref, max_chapters=8, max_chars=4000):
    """Assemble the cited passages for one entity, capped for cost."""
    out, total = [], 0
    for r in refs[:max_chapters]:
        t = text_by_ref.get(r)
        if not t:
            continue
        if total + len(t) > max_chars and out:
            break
        out.append(f"[{r}] {t}")
        total += len(t)
    return "\n\n".join(out)


def messages_call(model, system, user, max_tokens=90, timeout=60):
    body = {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}]}
    req = urllib.request.Request(API + "/messages", data=json.dumps(body).encode(), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    text = "".join(b.get("text", "") for b in d["content"] if b["type"] == "text").strip()
    return text, d["usage"]


# ---- prompts ----------------------------------------------------------------
GEN_SYSTEM = (
    "You are a classical scholar writing ultra-concise glosses for an index to "
    "Herodotus' Histories. Given the passages where a name appears, write ONE "
    "sentence identifying who they are: role or title, place, and their part in "
    "the narrative. Include approximate dates ONLY for well-established historical "
    "rulers (e.g. 'r. 570–526 BC'); otherwise omit dates entirely. Ground every "
    "claim in the provided passages or uncontroversial historical fact — never "
    "speculate or invent. If the passages say little, keep it minimal (e.g. 'A "
    "Persian, son of Otanes, in Xerxes' army.'). Output ONLY the gloss sentence: "
    "no preamble, no 'X was', do not restart with the name. If the passages do not "
    "actually identify this person — they are not clearly named, or there is nothing "
    "to say — reply with exactly the single word UNKNOWN and nothing else."
)

VER_SYSTEM = (
    "You fact-check one-line glosses for an index to Herodotus' Histories. Given a "
    "name, a proposed gloss, and the source passages, judge whether the gloss is "
    "accurate, supported (by the passages or uncontroversial history), and concise. "
    "Reply with STRICT JSON only: {\"ok\": true} if it is fine, or "
    "{\"ok\": false, \"fixed\": \"corrected one-sentence gloss\"} if it has an "
    "unsupported claim, a wrong fact, or a fabricated/uncertain date. Fixes must be "
    "one sentence in the same terse style, dates only for well-attested rulers."
)


def gen_user(name, ctx):
    return f"Name: {name}\n\nPassages from Herodotus (book.chapter):\n{ctx or '(no passage text available)'}"


def ver_user(name, gloss, ctx):
    return (f"Name: {name}\nProposed gloss: {gloss}\n\nSource passages:\n{ctx or '(none)'}")
