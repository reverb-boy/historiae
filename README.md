# Historiae — an interactive map of the world of Herodotus

A pannable, zoomable map of **every place named in Herodotus' *Histories*** —
over four hundred cities, sanctuaries, battlefields, rivers, islands, and the
far-off nations at the edges of the earth — each placed at its real location and
drawn from the text itself.

**The deliverable is a single self-contained file: [`herodotus-map.html`](herodotus-map.html).**
Double-click to open it in any browser. All code and content are embedded; only
the map's tile imagery streams from the network (as with any web map).

## Features

- **~387 places** on a real basemap, colour-coded by kind (capital, city,
  sanctuary, battle, river/water, island/landmark, region/nation).
- **Google-style zoom decluttering** — the great places (Athens, Sardis, Susa,
  Babylon, Memphis, Delphi…) show first; the lesser ones appear as you zoom in,
  and by deep zoom **every place is labelled**. Ranking is by **mention-frequency
  in the text**. Zoom goes to street level.
- **Click any place** → a card with its category, region, book/chapter citations,
  and — for the major places — a hand-written note and a cited passage. Minor
  places get an auto-stub (category, region, and every passage that names them)
  plus a link to the Pleiades gazetteer.
- **Peoples / ethnography layer** — 19 nations with Herodotus' notes.
- **Search** anything; **filter by book** (I–IX); **selection glow** on the chosen
  place; **"Modern places & borders"** toggle for bare terrain; **Sepia** tint.

Controls and the info card live on the **right**; the map fills the rest.
(Narrative routes were in an earlier version and are parked for a redesign.)

## How the gazetteer is built (the data pipeline)

The places are not hand-typed — they're extracted from the text and geolocated,
then merged with hand-written entries:

```
data/raw/hdt.perseus-eng2.xml   Perseus' Godley translation (TEI), with every
                                place tagged inline + coordinates + book/chapter
data/raw/tt_places.geojson      ToposText gazetteer (Greek names, Pleiades ids)

extract.py     TEI  -> data/places_raw.json   (977 named places; 324 with coords,
               aggregated by place with mention counts + book.chapter refs)
build_data.py  places_raw + ToposText + the 45 curated entries
               -> src/data_places.js  (HERODOTUS.places = [...387])
                  · recovers coords for no-coord places via ToposText name-match
                  · dedupes Perseus' multi-key duplicates
                  · scrubs modern/anachronistic geocodes (Constantinople→Byzantium,
                    Luxor→Thebes, Assuan→Syene; drops Cairo, Suez, Crimea, …)
                  · categorises by feature type, ranks by mentions into zoom tiers
                  · merges hand-authored blurbs/quotes (data/places_curated.json)
```

Regenerate the dataset:

```bash
python3 extract.py       # TEI  -> data/places_raw.json
python3 build_data.py    # -> src/data_places.js
python3 build.py         # inline everything -> herodotus-map.html
```

## Project layout

```
src/data.js         books, peoples, (parked) routes
src/data_places.js  GENERATED places[] (do not hand-edit)
src/app.js          map + UI (canvas markers, zoom tiering, search, cards)
src/app.css         styles
src/template.html   shell with {{PLACEHOLDERS}}
build.py            inlines leaflet + sources -> herodotus-map.html
extract.py          Perseus TEI -> places_raw.json
build_data.py       places_raw + ToposText + curated -> data_places.js
data/               source datasets + intermediates
leaflet.js/.css     map library (inlined at build time)
```

## Data sources & attribution

- **Text & place annotations:** Herodotus, *Histories*, tr. A. D. Godley, via the
  **Perseus Digital Library** (`tlg0016.tlg001.perseus-eng2`) — CC-BY-SA.
- **Gazetteer (Greek names, Pleiades ids, coordinates):** **ToposText** — CC-BY.
- **Ancient-place identifiers:** **Pleiades** — CC-BY.
- **Basemap tiles:** © OpenStreetMap contributors, © CARTO.

Hand-written passages in the curated entries are **paraphrases** of Herodotus,
each tagged with its `book.chapter` citation. Coordinates are "good enough to
point at," not survey-grade. See `DESIGN.md` for the design and open questions.
