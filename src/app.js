/* ============================================================================
   Historiae — application logic
   Leaflet map + right-hand controls/search + info card. Vanilla JS.
   Places (415, generated) render on a canvas layer with Google-style
   zoom-tiered decluttering: majors first, minors revealed on zoom-in.
   (Narrative routes are parked for a later iteration — data.routes is unused.)
   ========================================================================== */
(function () {
  "use strict";

  const CAT = {
    capital:   { color: "#b8860b", label: "Capital / royal seat" },
    city:      { color: "#2c6e8f", label: "City / settlement" },
    sanctuary: { color: "#7b4fa0", label: "Sanctuary / oracle" },
    battle:    { color: "#c0392b", label: "Battle" },
    river:     { color: "#1a9aa0", label: "River / water" },
    landmark:  { color: "#8a6d3b", label: "Island / landmark" },
    region:    { color: "#6b8e23", label: "Region (area label)" },
    people:    { color: "#9c6b3f", label: "People / tribe" },
  };
  const PEOPLE_COLOR = "#9c6b3f";
  const ROMAN = ["", "I","II","III","IV","V","VI","VII","VIII","IX"];
  const RADIUS = { 1: 6.5, 2: 5, 3: 4, 4: 3 };
  const PLACE_TOTAL = HERODOTUS.places.length;
  let hoveredRec = null;

  /* ---- map ---------------------------------------------------------------- */
  const map = L.map("map", {
    center: [37, 30], zoom: 4, minZoom: 3, maxZoom: 13,
    worldCopyJump: true, attributionControl: true,
  });
  map.zoomControl.setPosition("bottomleft");
  window.__map = map;   // debug/testing handle
  const mapEl = document.getElementById("map");

  const baseModern = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    { subdomains: "abcd", maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' });
  const basePhysical = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png",
    { subdomains: "abcd", maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' });
  basePhysical.addTo(map);          // default: bare terrain (modern labels off)

  /* ---- layers ------------------------------------------------------------- */
  const placeCanvas = L.canvas({ padding: 0.5, tolerance: 10 });   // generous hit area
  const placesLayer = L.layerGroup().addTo(map);   // markers added/removed by tier
  const peoplesLayer = L.layerGroup().addTo(map);
  const highlightLayer = L.layerGroup().addTo(map);

  let placesOn = true, peoplesOn = false;          // peoples off by default

  /* ---- build place markers (not yet added; refresh() places them) --------- */
  // regions & peoples are spread text labels with NO pin (like a country name on
  // Google Maps); regions live in the Places layer, peoples in the Peoples layer.
  const placeRecs = [];    // point markers (dots)   — Places layer
  const areaRecs = [];     // region area labels     — Places layer
  const peopleRecs = [];   // people area labels     — Peoples layer

  function wire(m, rec, p) {
    m.on("click", function (e) { L.DomEvent.stop(e); selectPlace(p); });
    if (rec.kind === "point") {
      m.on("mouseover", function () { hoverOn(rec); });
      m.on("mouseout", function () { hoverOff(rec); });
    }
    m.on("tooltipopen", function (e) {                 // label is a hit target too
      const el = e.tooltip._container;
      if (!el) return;
      el.style.pointerEvents = "auto"; el.style.cursor = "pointer";
      el.onclick = function (ev) { ev.stopPropagation(); selectPlace(p); };
      el.onmouseenter = function () { hoverOn(rec); };
      el.onmouseleave = function () { hoverOff(rec); };
    });
  }

  HERODOTUS.places.forEach(function (p) {
    if (p.cat === "region" || p.cat === "people") {
      const isPeople = p.cat === "people";
      const m = L.marker([p.lat, p.lng], {
        icon: L.divIcon({ className: "area-anchor", html: "", iconSize: [0, 0] }),
        interactive: false, keyboard: false,
      });
      m.bindTooltip(p.name, { permanent: true, interactive: true, direction: "center",
        className: "area-label " + p.cat + (p.rank <= 1 ? " big" : "") });
      const rec = { data: p, marker: m, kind: "area", people: isPeople,
                    layer: isPeople ? "peoples" : "places", minZoom: p.minZoom, on: false, labelWanted: false };
      wire(m, rec, p); (isPeople ? peopleRecs : areaRecs).push(rec);
    } else {
      const c = (CAT[p.cat] || CAT.landmark).color;
      const baseR = RADIUS[p.rank] || 3;
      const m = L.circleMarker([p.lat, p.lng], {
        renderer: placeCanvas, radius: baseR,
        color: "#fff", weight: 1, fillColor: c, fillOpacity: 1, opacity: 1,
      });
      m.bindTooltip(p.name, { permanent: true, interactive: true, direction: "right", offset: [7, 0], className: "place-label" });
      const rec = { data: p, marker: m, baseR: baseR, color: c, kind: "point",
                    layer: "places", minZoom: p.minZoom, on: false, labelWanted: false };
      wire(m, rec, p); placeRecs.push(rec);
    }
  });
  const allRecs = placeRecs.concat(areaRecs, peopleRecs);

  let selectedRec = null;   // the currently searched/clicked place — stays pinned

  // hover + label helpers (work for point dots and pin-less area labels)
  function labelEl(rec) { const tt = rec.marker.getTooltip(); return tt && tt._container; }
  function showLabel(rec, show) { const el = labelEl(rec); if (el) el.style.display = show ? "" : "none"; }
  function hoverOn(rec) {
    hoveredRec = rec;
    if (rec.kind === "point") {
      rec.marker.setStyle({ radius: rec.baseR + 3, weight: 2, color: "#b8860b" });
      if (rec.marker.bringToFront) rec.marker.bringToFront();
    }
    showLabel(rec, true);
    const el = labelEl(rec); if (el) el.classList.add("hl");
    mapEl.style.cursor = "pointer";
  }
  function hoverOff(rec) {
    if (hoveredRec === rec) hoveredRec = null;
    if (rec.kind === "point") rec.marker.setStyle({ radius: rec.baseR, weight: 1, color: "#fff" });
    showLabel(rec, rec.labelWanted || rec === selectedRec);
    const el = labelEl(rec); if (el && rec !== selectedRec) el.classList.remove("hl");
    mapEl.style.cursor = "";
  }

  // greedy label declutter: show the most-mentioned labels whose box doesn't
  // overlap a higher-priority one; areas (regions/peoples) win over city dots.
  function labelBox(pt, name, centered, wpc) {
    const w = name.length * (wpc || 7.0) + 8, h = 17;
    return centered ? { x: pt.x - w / 2, y: pt.y - h / 2, w: w, h: h }
                    : { x: pt.x + 7, y: pt.y - h / 2, w: w, h: h };
  }
  function boxHits(a, placed) {
    for (let i = 0; i < placed.length; i++) {
      const b = placed[i];
      if (!(a.x > b.x + b.w || a.x + a.w < b.x || a.y > b.y + b.h || a.y + a.h < b.y)) return true;
    }
    return false;
  }
  function reserve(rec, placed) {
    const centered = rec.kind === "area" || rec.people;
    placed.push(labelBox(map.latLngToContainerPoint(rec.marker.getLatLng()), rec.data.name, centered, centered ? 9 : 7));
  }
  function declutterLabels() {
    const size = map.getSize();
    const placed = [];
    if (hoveredRec && hoveredRec.on) reserve(hoveredRec, placed);
    if (selectedRec && selectedRec !== hoveredRec && selectedRec.on) {
      showLabel(selectedRec, true); reserve(selectedRec, placed);
    }
    function lay(recs, centered, wpc) {
      recs.filter(function (r) { return r.on && r !== hoveredRec && r !== selectedRec; })
        .sort(function (a, b) { return (b.data.mentions || 0) - (a.data.mentions || 0); })
        .forEach(function (r) {
          const pt = map.latLngToContainerPoint(r.marker.getLatLng());
          if (pt.x < -80 || pt.y < -40 || pt.x > size.x + 80 || pt.y > size.y + 40) {
            r.labelWanted = false; showLabel(r, false); return;
          }
          const box = labelBox(pt, r.data.name, centered, wpc);
          if (!boxHits(box, placed)) { r.labelWanted = true; placed.push(box); showLabel(r, true); }
          else { r.labelWanted = false; showLabel(r, false); }
        });
    }
    lay(peopleRecs, true, 9);   // peoples (area labels) — top priority
    lay(areaRecs, true, 9);     // regions
    lay(placeRecs, false, 7);   // then the point dots
  }

  const recById = {};    // place id -> rec, for pinning the selected place
  allRecs.forEach(function (r) { recById[r.data.id] = r; });

  /* ---- the one function that decides what's visible ----------------------- */
  function refresh() {
    const z = map.getZoom();
    let visible = 0, hiddenByZoom = 0;
    allRecs.forEach(function (rec) {
      const layerOn = rec.layer === "peoples" ? peoplesOn : placesOn;
      const passZoom = rec.minZoom <= z;
      const want = layerOn && (passZoom || rec === selectedRec);   // selected stays pinned
      if (want && !rec.on) { rec.marker.addTo(placesLayer); rec.on = true; }
      else if (!want && rec.on) { placesLayer.removeLayer(rec.marker); rec.on = false; }
      if (rec.layer === "places" && rec !== selectedRec) { if (passZoom) visible++; else hiddenByZoom++; }
    });
    declutterLabels();
    updateHint(visible, hiddenByZoom);
  }
  function updateHint(visible, hiddenByZoom) {
    const hint = document.getElementById("zoomhint");
    if (placesOn && hiddenByZoom > 0) {
      hint.textContent = "Showing " + visible + " of " + (visible + hiddenByZoom) +
        " places here — zoom in for more";
      hint.classList.add("show");
    } else {
      hint.classList.remove("show");
    }
  }
  map.on("zoomend", refresh);
  map.on("moveend", declutterLabels);   // re-declutter labels after panning

  /* ======================================================================== */
  /*  RIGHT-PANEL UI                                                          */
  /* ======================================================================== */
  document.getElementById("count-places").textContent = PLACE_TOTAL;
  document.getElementById("count-peoples").textContent = peopleRecs.length;

  document.querySelectorAll('.toggle[data-layer]').forEach(function (el) {
    el.addEventListener("click", function () {
      const key = el.dataset.layer;
      const on = el.classList.toggle("on");
      if (key === "places") { placesOn = on; refresh(); }
      if (key === "peoples") { peoplesOn = on; refresh(); }
      if (key === "basemap") {
        if (on) { map.removeLayer(basePhysical); baseModern.addTo(map); }
        else { map.removeLayer(baseModern); basePhysical.addTo(map); }
      }
    });
  });

  // ---- legend ----
  const legendEl = document.getElementById("legend");
  Object.keys(CAT).forEach(function (k) {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = '<span class="dot" style="background:' + CAT[k].color + '"></span>' + CAT[k].label;
    legendEl.appendChild(item);
  });

  const CREDIT =
    PLACE_TOTAL + " places drawn from Herodotus, <i>Histories</i> (Books I–IX), extracted from the " +
    "Perseus text and geolocated via Perseus &amp; ToposText; citations are book.chapter. " +
    "Hand-written passages are paraphrased. Basemap © OpenStreetMap &amp; CARTO.";

  /* ======================================================================== */
  /*  SEARCH                                                                  */
  /* ======================================================================== */
  const searchEl = document.getElementById("search");
  const suggestEl = document.getElementById("suggest");
  // loose key: letters only, common Greek/Latin endings stripped, so spelling
  // variants match (Siphnos↔Siphnus, Cyme↔Kyme-ish, -us/-os/-um/-on)
  function looseKey(s) {
    return String(s || "").toLowerCase().replace(/[^a-z]/g, "").replace(/(us|os|um|on|es|ai|oi|e|a)$/, "");
  }
  const searchIndex = allRecs.map(function (rec) {
    const d = rec.data;
    return { rec: rec, kind: "place", name: d.name,
      hay: (d.name + " " + (d.aka || "") + " " + (d.region || "") + " " + (d.blurb || "")).toLowerCase(),
      loose: looseKey(d.name), gloss: d.blurb || d.gloss || "",
      color: (CAT[d.cat] || CAT.landmark).color, sub: d.region || CAT[d.cat].label };
  }).concat((HERODOTUS.persons || []).map(function (p) {
    return { person: p, kind: "person", name: p.name, hay: p.name.toLowerCase(),
      loose: looseKey(p.name), color: "#7a5c8a", gloss: p.gloss || "",
      sub: "person · " + p.mentions + " mention" + (p.mentions > 1 ? "s" : "") };
  })).concat((HERODOTUS.names || []).map(function (n) {
    var isPeople = n.type === "ethnic";
    return { nm: n, kind: "name", name: n.name,
      hay: (n.name + " " + (n.gloss || "")).toLowerCase(),
      loose: looseKey(n.name), color: isPeople ? "#9c6b3f" : "#4c7d8c", gloss: n.gloss || "",
      sub: (isPeople ? "people" : "place") + " · " + n.mentions + " mention" + (n.mentions > 1 ? "s" : "") };
  }));

  // --- cross-reference lookup: normalized name -> best search hit --------------
  // lets us turn any known name that appears inside a gloss into a link.
  function hitMentions(x) { return (x.rec ? x.rec.data.mentions : x.person ? x.person.mentions : x.nm ? x.nm.mentions : 0) || 0; }
  const xrefMap = new Map();
  let xrefMaxWords = 1;
  searchIndex.forEach(function (x) {
    const key = x.name.toLowerCase();
    if (!key) return;
    const prev = xrefMap.get(key);
    if (!prev || hitMentions(x) > hitMentions(prev)) xrefMap.set(key, x);   // prefer the more-mentioned sense
    const wc = key.split(/\s+/).length;
    if (wc > xrefMaxWords) xrefMaxWords = wc;
  });
  if (xrefMaxWords > 4) xrefMaxWords = 4;   // bound the match window

  // Render gloss/blurb text with every known name turned into a clickable xref
  // (except self-references). Escapes all non-link text.
  function linkify(text, selfName) {
    if (!text) return "";
    const selfKey = String(selfName || "").toLowerCase();
    const parts = String(text).split(/([A-Za-zÀ-ɏ]+)/);   // even = separators, odd = words
    let out = "", i = 0;
    while (i < parts.length) {
      if (i % 2 === 0) { out += esc(parts[i]); i++; continue; }
      let matched = null, endIdx = i;
      for (let wc = xrefMaxWords; wc >= 1; wc--) {
        const lastPi = i + (wc - 1) * 2;
        if (lastPi >= parts.length) continue;
        const cand = parts.slice(i, lastPi + 1).join("");
        const key = cand.toLowerCase();
        if (key !== selfKey && xrefMap.has(key)) { matched = xrefMap.get(key); endIdx = lastPi; break; }
      }
      if (matched) {
        out += '<a class="xref" data-name="' + esc(matched.name) + '">' + esc(parts.slice(i, endIdx + 1).join("")) + "</a>";
        i = endIdx + 1;
      } else { out += esc(parts[i]); i++; }
    }
    return out;
  }

  // dispatch a search hit to the right selector (shared by suggestions + xrefs)
  function dispatchHit(h) {
    if (!h) return;
    searchEl.value = h.name; syncClear(); closeSuggest();
    if (h.kind === "person") selectPerson(h.person);
    else if (h.kind === "name") selectName(h.nm);
    else selectPlace(h.rec.data);
  }

  const searchWrap = searchEl.closest(".search-wrap");
  const clearBtn = document.getElementById("search-clear");
  function syncClear() { searchWrap.classList.toggle("has-text", searchEl.value.length > 0); }
  clearBtn.addEventListener("click", function () {
    searchEl.value = ""; syncClear(); closeSuggest(); searchEl.focus();
  });

  let sugActive = -1;
  searchEl.addEventListener("input", function () { syncClear(); runSearch(searchEl.value); });
  searchEl.addEventListener("focus", function () { if (searchEl.value) runSearch(searchEl.value); });
  searchEl.addEventListener("keydown", function (e) {
    const items = suggestEl.querySelectorAll(".sug");
    if (e.key === "ArrowDown") { e.preventDefault(); sugActive = Math.min(sugActive + 1, items.length - 1); paintActive(items); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sugActive = Math.max(sugActive - 1, 0); paintActive(items); }
    else if (e.key === "Enter") { if (items[sugActive]) items[sugActive].click(); }
    else if (e.key === "Escape") { closeSuggest(); }
  });
  document.addEventListener("click", function (e) { if (!e.target.closest(".search-wrap")) closeSuggest(); });
  function paintActive(items) {
    items.forEach(function (it, i) { it.classList.toggle("active", i === sugActive); });
    if (items[sugActive]) items[sugActive].scrollIntoView({ block: "nearest" });
  }
  function closeSuggest() { suggestEl.classList.remove("open"); sugActive = -1; }
  function runSearch(q) {
    q = q.trim().toLowerCase();
    if (!q) { closeSuggest(); return; }
    // rank: name-startswith first, then name-contains, other fields, then loose
    const ql = looseKey(q);
    const scored = [];
    searchIndex.forEach(function (x) {
      const n = x.name.toLowerCase();
      let s = -1;
      if (n === q) s = 0; else if (n.indexOf(q) === 0) s = 1;
      else if (n.indexOf(q) !== -1) s = 2; else if (x.hay.indexOf(q) !== -1) s = 3;
      else if (ql.length >= 3 && x.loose.indexOf(ql) === 0) s = 4;   // spelling-tolerant
      if (s >= 0) scored.push({ x: x, s: s });
    });
    scored.sort(function (a, b) {
      if (a.s !== b.s) return a.s - b.s;
      return hitMentions(b.x) - hitMentions(a.x);
    });
    const hits = scored.slice(0, 10).map(function (o) { return o.x; });
    if (!hits.length) {
      suggestEl.innerHTML = '<div class="sug" style="cursor:default;color:#8a7a5c">No match in the nine books.</div>';
      suggestEl.classList.add("open"); sugActive = -1; return;
    }
    suggestEl.innerHTML = "";
    hits.forEach(function (h) {
      const el = document.createElement("div");
      el.className = "sug";
      el.innerHTML =
        '<div class="sug-top"><span class="dot" style="background:' + h.color + '"></span>' +
        '<span class="nm">' + esc(h.name) + "</span>" +
        '<span class="meta">' + esc(h.sub || h.kind) + "</span></div>" +
        (h.gloss ? '<div class="sug-gloss">' + esc(h.gloss) + "</div>" : "");
      el.addEventListener("click", function () { dispatchHit(h); });
      suggestEl.appendChild(el);
    });
    suggestEl.classList.add("open"); sugActive = -1;
  }

  /* ======================================================================== */
  /*  SELECTION HIGHLIGHT                                                      */
  /* ======================================================================== */
  function highlightAt(lat, lng) {
    highlightLayer.clearLayers();
    const icon = L.divIcon({ className: "pin-highlight", html: "<span></span>", iconSize: [30, 30], iconAnchor: [15, 15] });
    L.marker([lat, lng], { icon: icon, interactive: false, zIndexOffset: 1000 }).addTo(highlightLayer);
  }
  function clearHighlight() { highlightLayer.clearLayers(); }

  /* ======================================================================== */
  /*  INFO CARD                                                               */
  /* ======================================================================== */
  const infoHead = document.getElementById("info-head");
  const infoTitle = document.getElementById("info-title");
  const infoAka = document.getElementById("info-aka");
  const infoBadges = document.getElementById("info-badges");
  const infoBody = document.getElementById("info-body");

  // --- navigation history (Back arrow) ---------------------------------------
  const backBtn = document.getElementById("info-back");
  const navStack = [];      // entries: [selectFn, argument]
  let navGuard = false;     // true while replaying a Back step, so we don't re-push
  function pushNav(fn, arg) {
    if (navGuard) return;
    const top = navStack[navStack.length - 1];
    if (top && top[0] === fn && top[1] === arg) return;   // ignore re-selecting the same entry
    navStack.push([fn, arg]);
    syncBack();
  }
  function syncBack() { if (backBtn) backBtn.style.display = navStack.length > 1 ? "inline-flex" : "none"; }
  function goBack() {
    if (navStack.length < 2) return;
    navStack.pop();                                   // drop the current entry
    const prev = navStack[navStack.length - 1];
    navGuard = true; prev[0](prev[1]); navGuard = false;
    syncBack();
  }
  if (backBtn) backBtn.addEventListener("click", goBack);

  map.on("click", function () { showPlaceholder(); });
  function openInfo() { infoHead.style.display = ""; }
  function showPlaceholder() {
    infoHead.style.display = "none";
    infoBody.innerHTML =
      '<div class="placeholder"><p>Search above, or click any place on the map, ' +
      'to read what Herodotus reports of it.</p><p class="cx">' + CREDIT + "</p></div>";
    clearHighlight();
    if (selectedRec) { selectedRec = null; refresh(); }   // unpin the old selection
  }

  function booksLine(books) {
    if (!books || !books.length) return "";
    return '<div class="books-line"><b>Appears in:</b> ' +
      books.map(function (b) { return "Book " + ROMAN[b]; }).join(", ") + "</div>";
  }
  function quoteBlock(q) {
    if (!q) return "";
    return '<blockquote class="quote">' + esc(q.text) + '<span class="cite">— Herodotus ' + esc(q.cite) + "</span></blockquote>";
  }
  function refsBlock(refs, term) {
    if (!refs || !refs.length) return "";
    const chip = function (r) {
      return '<span class="r ref" data-ref="' + esc(r) + '" data-term="' + esc(term || "") + '">' + esc(r) + "</span>";
    };
    const shown = refs.slice(0, 40).map(chip).join("");
    const more = refs.length > 40 ? " <span class=\"r\">+" + (refs.length - 40) + " more</span>" : "";
    return '<div class="refs"><b>Mentioned at</b> ' + shown + more + "</div>";
  }
  function baseName(s) { return String(s || "").replace(/\s*\([^)]*\)\s*$/, "").trim(); }
  function booksOf(refs) {
    const s = new Set();
    (refs || []).forEach(function (r) { const b = parseInt(r, 10); if (b) s.add(b); });
    return Array.from(s).sort(function (a, b) { return a - b; });
  }

  function selectPlace(p) {
    pushNav(selectPlace, p);
    const cat = CAT[p.cat] || CAT.landmark;
    const term = baseName(p.name);
    infoTitle.textContent = p.name;
    infoAka.textContent = p.aka || "";
    let badges = '<span class="badge cat" style="background:' + cat.color + '">' + cat.label + "</span>";
    if (p.region) badges += '<span class="badge region">' + esc(p.region) + "</span>";
    if (p.mentions) badges += '<span class="badge">' + p.mentions + " mention" + (p.mentions > 1 ? "s" : "") + "</span>";
    infoBadges.innerHTML = badges;

    let body;
    if (p.blurb) {
      body = '<p class="blurb">' + linkify(p.blurb, p.name) + "</p>" + quoteBlock(p.quote) + booksLine(p.books) + refsBlock(p.refs, term);
    } else {
      body = (p.gloss ? '<p class="blurb">' + linkify(p.gloss, p.name) + "</p>" : "") +
        refsBlock(p.refs, term) + booksLine(p.books);   // badges carry cat/region/count
    }
    if (p.pleiades) {
      body += '<p class="ext"><a href="https://pleiades.stoa.org/places/' + esc(p.pleiades) +
        '" target="_blank" rel="noopener">View in the Pleiades gazetteer ↗</a></p>';
    }
    infoBody.innerHTML = body;
    openInfo();
    selectedRec = recById[p.id] || null;      // pin it (stays visible when zoomed out)
    highlightAt(p.lat, p.lng);
    refresh();
    map.flyTo([p.lat, p.lng], Math.max(map.getZoom(), p.minZoom, 6), { duration: 0.7 });
  }

  function selectPerson(p) {
    pushNav(selectPerson, p);
    infoTitle.textContent = p.name;
    infoAka.textContent = "a person named in the Histories";
    infoBadges.innerHTML = '<span class="badge cat" style="background:#7a5c8a">Person</span>' +
      '<span class="badge">' + p.mentions + " mention" + (p.mentions > 1 ? "s" : "") + "</span>";
    infoBody.innerHTML = (p.gloss ? '<p class="blurb">' + linkify(p.gloss, p.name) + "</p>" : "") +
      refsBlock(p.refs, p.name) + booksLine(booksOf(p.refs));
    openInfo();
    if (selectedRec) { selectedRec = null; refresh(); }   // person has no map location
    clearHighlight();
  }

  function selectName(n) {
    pushNav(selectName, n);
    var isPeople = n.type === "ethnic";
    var term = baseName(n.name);
    infoTitle.textContent = n.name;
    infoAka.textContent = isPeople ? "a people named in the Histories"
                                   : "a place named in the Histories";
    infoBadges.innerHTML =
      '<span class="badge cat" style="background:' + (isPeople ? "#9c6b3f" : "#4c7d8c") + '">' +
      (isPeople ? "People" : "Place") + "</span>" +
      '<span class="badge">' + n.mentions + " mention" + (n.mentions > 1 ? "s" : "") + "</span>";
    infoBody.innerHTML = (n.gloss ? '<p class="blurb">' + linkify(n.gloss, n.name) + "</p>" : "") +
      refsBlock(n.refs, term) + booksLine(booksOf(n.refs));
    openInfo();
    if (selectedRec) { selectedRec = null; refresh(); }   // not on the map
    clearHighlight();
  }

  /* ======================================================================== */
  /*  READER  (the Herodotus text)                                            */
  /* ======================================================================== */
  const app = document.getElementById("app");
  const readerBody = document.getElementById("reader-body");
  const readerTitle = document.getElementById("reader-title");
  const readerToggle = document.getElementById("reader-toggle");
  const BOOK_NAME = {}; (HERODOTUS.books || []).forEach(function (b) { BOOK_NAME[b.n] = b.name; });
  let currentBook = null;

  function cssId(cn) { return String(cn).replace(/[^a-z0-9]/gi, "_"); }
  function bookLabel(bn) { return "Book " + (ROMAN[+bn] || bn) + (BOOK_NAME[+bn] ? " · " + BOOK_NAME[+bn] : ""); }

  function renderBook(bn) {
    if (currentBook === bn) return;
    currentBook = bn;
    let html = '<div class="rbook">' + esc(bookLabel(bn)) + "</div>";
    (HERODOTUS_TEXT[bn] || []).forEach(function (pair) {
      // each chapter is its own paragraph; pair[1] is pre-escaped HTML with <n> names
      html += '<p class="rch" id="rch-' + bn + "-" + cssId(pair[0]) + '">' +
        '<span class="rn">' + esc(pair[0]) + "</span>" + pair[1] + "</p>";
    });
    readerBody.innerHTML = html;
    readerTitle.textContent = bookLabel(bn).replace(" · ", " — ");
  }
  function highlightChapter(bn, cn, term) {
    // clear any previous highlight
    readerBody.querySelectorAll(".rch.target").forEach(function (x) { x.classList.remove("target"); });
    readerBody.querySelectorAll("n.mark").forEach(function (x) { x.classList.remove("mark"); });
    const el = document.getElementById("rch-" + bn + "-" + cssId(cn));
    if (!el) return;
    el.classList.add("target");
    if (term) {                              // mark the matching name(s) in the chapter
      const tl = term.toLowerCase();
      el.querySelectorAll("n").forEach(function (n) {
        if (n.textContent.toLowerCase().indexOf(tl) !== -1) n.classList.add("mark");
      });
    }
    el.scrollIntoView({ block: "center" });
  }
  function openReaderPanel() {
    if (!app.classList.contains("reader-open")) {
      app.classList.add("reader-open"); readerToggle.textContent = "‹";
      setTimeout(function () { map.invalidateSize(); }, 280);
    }
  }
  function closeReader() {
    app.classList.remove("reader-open"); readerToggle.textContent = "›";
    setTimeout(function () { map.invalidateSize(); }, 280);
  }
  function toggleReader() {
    if (app.classList.contains("reader-open")) closeReader();
    else { openReaderPanel(); if (!currentBook) renderBook("1"); }
  }
  function openReaderRef(ref, term) {
    const dot = ref.indexOf(".");
    if (dot < 0) return;
    const bn = ref.slice(0, dot), cn = ref.slice(dot + 1);
    openReaderPanel();
    renderBook(bn);
    highlightChapter(bn, cn, term);
  }
  readerToggle.addEventListener("click", toggleReader);
  document.getElementById("reader-close").addEventListener("click", closeReader);
  // clicking a name in the text puts it in the search bar and searches for it
  readerBody.addEventListener("click", function (e) {
    const n = e.target.closest("n");
    if (!n) return;
    e.stopPropagation();          // don't let the global handler close the suggestions
    const q = n.textContent.trim();
    searchEl.value = q; syncClear(); runSearch(q); searchEl.focus();
  });
  // clicking a "Mentioned at 1.72" chip jumps to that passage with the term marked
  infoBody.addEventListener("click", function (e) {
    const xr = e.target.closest(".xref");
    if (xr) { e.preventDefault(); dispatchHit(xrefMap.get(String(xr.dataset.name || "").toLowerCase())); return; }
    const el = e.target.closest(".ref");
    if (el) openReaderRef(el.dataset.ref, el.dataset.term || "");
  });

  /* ======================================================================== */
  /*  TOP-BAR + INTRO                                                          */
  /* ======================================================================== */
  document.getElementById("btn-reader").addEventListener("click", function () { toggleReader(); });
  const intro = document.getElementById("intro");
  document.getElementById("intro-go").addEventListener("click", function () {
    intro.classList.add("hidden"); setTimeout(function () { map.invalidateSize(); refresh(); }, 50);
  });
  document.getElementById("btn-help").addEventListener("click", function () { intro.classList.remove("hidden"); });
  intro.addEventListener("click", function (e) { if (e.target === intro) intro.classList.add("hidden"); });

  setTimeout(function () { map.invalidateSize(); refresh(); }, 200);
  window.addEventListener("resize", function () { map.invalidateSize(); });
  refresh();
  showPlaceholder();

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();
