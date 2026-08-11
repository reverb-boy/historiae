# Historiae — an interactive map of the world of Herodotus

*Design doc, v0.2 — updated after the first review.*

**Changelog v0.1 → v0.2**
- ❌ **Narrative routes removed** — parked for a later iteration (we'll redesign them).
- 🧹 Removed the redundant colour swatch on the "Peoples & nations" toggle.
- ➕ **"Modern places & borders" toggle** — strip the map back to bare terrain.
- ➕ **Selection glow** — a searched/clicked place pulses with a gold ring.
- 🎯 **New core direction:** exhaustively screen the text for *every* place, and
  render them with **Google-style zoom-tiered decluttering** (majors first,
  minors on zoom-in). This is now the heart of the app (§5, §6).

---

## 1. What it is

A pannable, zoomable web map — Google-Maps-like in feel — of the world as it
appears in Herodotus' *Histories*. Every place the text names sits on a real
basemap at its true coordinates, with what Herodotus reports about it. Ships as
**one self-contained `herodotus-map.html`** (only the map tile imagery streams
from the network).

---

## 2. What's built now (v0.2)

- Real basemap (Carto Voyager) with a **"Modern places & borders" toggle** that
  swaps to a bare no-labels terrain; plus a **Sepia** tint toggle.
- **45 places** (colour-coded: capital, city, sanctuary, battle, river, landmark)
  and **19 peoples** (territory discs), each with a cited passage.
- **Click-for-info card** on the right; **search** with type-ahead; **filter by
  book** I–IX (dims what's outside the chosen book).
- **Selection glow** — searching or clicking a place drops a pulsing gold ring on it.

The 45 places are a hand-curated seed. §5 is about growing that to *everything*.

---

## 3. The big goal: every place in Herodotus

> *"screen the book text and find all of them — that's the purpose of this app."*

Herodotus names on the order of **~900 place-mentions → ~350–450 distinct
locations** across the nine books (cities, sanctuaries, battle sites, rivers,
mountains, regions, and the seats of peoples). v0.2 has 45 of them. The goal is
to cover the long tail.

### 3a. Where the data comes from

Hand-extracting hundreds of toponyms + coordinates from raw text is slow and
error-prone (Greek spellings, duplicates, places that no longer exist). Better to
**seed from an existing scholarly geo-dataset of Herodotus**, then enrich. Candidate
sources (I'll confirm availability + licence as step 1):

| Source | What it gives | Licence |
|---|---|---|
| **ToposText** | Herodotus fully indexed; every place-mention linked to coordinates + the exact passage | CC-BY (attribution) |
| **Pleiades** | The coordinate backbone — CC-BY gazetteer of ancient places | CC-BY |
| **Hestia project** | Academic project that geo-referenced *all* place-names in Herodotus (Godley translation), linked to Pleiades | check |
| **Perseus / Godley** | Public-domain English text — to pull the passage context per place | public domain |

### 3b. Pipeline options (needs your call — see §7)

- **Plan A — dataset-driven (recommended for completeness).** Ingest the ToposText/
  Hestia Herodotus place list → coords + book.chapter refs + Pleiades ID → dedupe →
  auto-assign category & importance. Most accurate and complete; least fabrication.
- **Plan B — text-driven.** NER/LLM pass over the full Godley/Rawlinson text to pull
  every toponym + citation, then geocode against Pleiades and verify. More editorial
  control, more noise, needs a verification pass.
- **Plan C — hybrid.** Dataset for the authoritative list/coords/refs, text pass to
  enrich prose and catch anything the dataset misses. Best quality, most work.

### 3c. Prose for hundreds of places

We can't hand-write a rich paragraph for all ~400. Proposed tiering of *content*
(separate from the *visual* tiering in §6):
- **Major places** — full hand-authored blurb + chosen pull-quote (like today's 45).
- **Secondary** — a 1–2 sentence note, still human-checked.
- **Long tail** — an auto-generated stub: category, region, and the *linked
  passage(s)* where Herodotus names it (`"named at 4.99, 4.101"`), so the card is
  always useful even without prose.

---

## 4. Data model (extended)

```
place = {
  id, name, aka, lat, lng,
  cat,                 // capital | city | sanctuary | battle | river | region | landmark
  region, books[],
  rank,                // 1 (major) … 4 (minor) — drives size + zoom visibility (§6)
  mentions,            // # of chapters that name it — the basis for rank
  refs[],              // ["1.72","1.75",…] book.chapter citations
  blurb, quote{ text, cite },   // blurb/quote optional for the long tail
  pleiades             // source id for provenance
}
```

Peoples keep their current shape (+ `rank`). Routes stay in the data file, unused,
until we redesign that feature.

---

## 5. Rendering hundreds of markers

- Draw place markers on an **`L.canvas` renderer** (not one SVG node each) so 400+
  points stay smooth to pan/zoom.
- **No clustering** — clustering hides the geography, which is the whole point.
  Use zoom-tiering (§6) instead.
- Labels (name tooltips) shown only for the tiers currently "promoted" at the
  active zoom, to avoid a wall of text.

---

## 6. Zoom-tiered decluttering (the "Google" behaviour)

Assign every place a **`rank` 1–4**, derived mainly from **mention-frequency** in
the text (how many chapters name it) with manual boosts for narratively pivotal
spots (Thermopylae, Marathon…). Then gate visibility by zoom:

| rank | examples | appears at zoom ≥ | dot size | label |
|---|---|---|---|---|
| 1 major | Athens, Sparta, Sardis, Susa, Babylon, Memphis, Delphi | 3 | large | always |
| 2 notable | Miletus, Cyrene, Ecbatana, Naxos, Sinope | 5 | med | at zoom ≥5 |
| 3 minor | lesser towns, tributaries | 6 | small | on hover |
| 4 trace | one-off villages, obscure tribes | 7–8 | dot | on hover |

Implementation: a `zoomend` handler shows/hides each marker by
`place.minZoom(rank) <= map.getZoom()`. Zooming in progressively reveals the
denser detail — exactly like Google Maps' label density. A small on-map hint
("zoom in for more places") can cue it.

---

## 7. Decisions (locked 2026-08-11)

- **A. Pipeline → Hybrid.** Dataset for the authoritative list/coords/refs; text pass to enrich prose and catch gaps.
- **B. Scope → Everything (~350–450).** Cities, sanctuaries, battles, rivers, mountains, regions, seats of peoples. Zoom-tiering keeps it readable.
- **C. Long-tail prose → Stubs.** Rich blurbs + quotes for majors; terse auto-stubs (category, region, linked passages) for minors so every card is useful immediately.
- D (borders) and E (verbatim quotes) still open; E leans verbatim since the dataset carries exact passages.

## 8. Build plan for the gazetteer — ✅ DONE (v0.3)

1. ✅ **Acquire** — used the **Perseus Godley TEI**, which tags every place inline
   with a Getty TGN id, coordinates, and book/chapter position; enriched with the
   **ToposText** GeoJSON (Greek names, Pleiades ids). Both CC-BY / CC-BY-SA.
2. ✅ **Normalise** (`extract.py` + `build_data.py`) → `{name, coords, cat, refs[],
   mentions, rank, minZoom, aka, pleiades}`; recovered no-coord places via
   ToposText name-match; deduped Perseus multi-key duplicates.
3. ✅ **Merge** the 45 hand-authored entries (blurbs/quotes preserved; battles &
   sanctuaries keep their curated category).
4. ✅ **Render** on an `L.canvas` layer with zoom-tiered visibility (§6).
   **Result: 407 places** — 23 major (zoom 3), 75 (zoom 5), 84 (zoom 6), 225 (zoom 7).
5. ⏳ **Enrich** prose for the long tail over time (stubs show refs + Pleiades link now).

## 9. Open questions for you

- **A. Data pipeline (§3b).** Plan A (dataset-driven, most complete), B
  (text-driven, most editorial control), or C (hybrid, best + most work)?
- **B. What counts as "a place"?** Everything (~350–450, incl. rivers, mountains,
  minor tribes, regions) — or settlements + sanctuaries + battles only (~150),
  keeping tribes in the existing Peoples layer?
- **C. Long-tail prose (§3c).** OK with rich blurbs for majors + terse
  auto-stubs (category + linked passages) for the minor tail? Or hold minors out
  until each can be written up properly?
- **D. Borders.** The no-labels base still shows faint modern borders. Want a true
  **physical basemap** (no borders at all, more antique) as the "off" state?
- **E. Quotations.** Still paraphrase + cite, or wire in a public-domain
  translation (Godley/Rawlinson) so passages are verbatim? (The dataset route in §3
  makes verbatim linking natural, since ToposText carries the exact passages.)

---

*v0.2 code (routes removed, basemap toggle, selection glow) is built and verified.
The exhaustive-gazetteer work (§3, §5, §6) is spec'd but not started — it waits on
§7A–C so I build the right thing once.*
