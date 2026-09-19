/* harbor.js - a to-scale plan view of the waterfront, drawn as inline SVG.
 *
 * No dependencies, no build step. Loaded with a plain <script>, it defines:
 *
 *   const view = Harbor.create(container, { onSelect });
 *   view.setBerths(berths);                          // [{id, name, length_ft, capacity_mode}]
 *   view.setDay(dayIso, occupantsByBerthId, flags);  // who sits where today, and what the rules found
 *   view.destroy();
 *
 * THE SCALE. The SVG viewBox is measured in FEET: 1 SVG unit = 1 foot, so a 120 ft
 * hull is a 120-unit path and the 410 ft pier face is a 410-unit line. The browser
 * stretches the viewBox to the container's width, so pixels per foot = container
 * width / viewBox width (a 600 ft map in a 600 px box is 1 px per ft), and every
 * berth and hull shares that one scale. The 100 ft scale bar is just a 100-unit line.
 *
 * WHAT THIS FILE DOES NOT DO. It never decides whether a booking is allowed. The
 * rules engine (dock/rules.py) decides, and the app passes its verdicts in as
 * `flags`; this file only turns them into red outlines, stripes, dashes and badges.
 * The only arithmetic here is drawing arithmetic: where a hull sits along a face,
 * and how far a too-long hull sticks out past the end.
 */
(function () {
'use strict';

/* ---- 1. Colours and styles, injected once. Custom properties live on the container so
   the same map works on any page; dark mode comes from the OS setting or from
   data-theme="dark" / "light" on <html>, and the explicit attribute always wins. ---- */
const LIGHT = `
  color-scheme: light;
  --hb-surface: #fcfcfb; --hb-ink: #0b0b0b; --hb-ink-2: #52514e; --hb-muted: #898781;
  --hb-border: rgba(11, 11, 11, .10);
  --hb-water: #dde8f4; --hb-land: #ece9df; --hb-pier: #cfcdc3; --hb-pier-edge: #898781;
  --hb-rv: #2a78d6; --hb-motor: #eb6834; --hb-fv: #1baf7a; --hb-sail: #eda100;
  --hb-barge: #e87ba4; --hb-tug: #008300; --hb-osv: #4a3aa7; --hb-other: #898781;
  --hb-critical: #d03b3b; --hb-on-critical: #ffffff; --hb-warning: #fab219; --hb-on-warning: #0b0b0b;`;
const DARK = `
  color-scheme: dark;
  --hb-surface: #1a1a19; --hb-ink: #ffffff; --hb-ink-2: #c3c2b7; --hb-muted: #898781;
  --hb-border: rgba(255, 255, 255, .10);
  --hb-water: #16263a; --hb-land: #262622; --hb-pier: #45443f; --hb-pier-edge: #898781;
  --hb-rv: #3987e5; --hb-motor: #d95926; --hb-fv: #199e70; --hb-sail: #c98500;
  --hb-barge: #d55181; --hb-tug: #008300; --hb-osv: #9085e9; --hb-other: #898781;`;

const CSS = `
.harbor {${LIGHT}}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .harbor {${DARK}} }
:root[data-theme="dark"] .harbor {${DARK}}

/* The map box scrolls sideways on a narrow phone so labels stay legible; the page never does. */
.harbor-map { position: relative; overflow-x: auto; border: 1px solid var(--hb-border);
              border-radius: 12px; background: var(--hb-water); }
.harbor-svg { display: block; width: 100%; min-width: 560px; height: auto; }
.harbor-svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.harbor .land { fill: var(--hb-land); }
.harbor .deck { fill: var(--hb-pier); stroke: var(--hb-pier-edge); stroke-width: .8; }
.harbor .lbl { fill: var(--hb-ink-2); font-size: 11px; }
.harbor .lbl.small { fill: var(--hb-muted); font-size: 10px; }
.harbor .chrome line, .harbor .chrome path { stroke: var(--hb-ink-2); stroke-width: 1.5; fill: none; }
.harbor .hatch-bg { fill: var(--hb-surface); }
.harbor .hatch-line { stroke: var(--hb-ink-2); stroke-width: 1.5; }
.harbor .hatch-grey { stroke: var(--hb-muted); stroke-width: 1.2; }
.harbor .stripe-line { stroke: var(--hb-critical); stroke-width: 2; }

/* Berth faces: a fender line; a slip is a dashed box. The rules' verdicts colour them. */
.harbor .berth-line { stroke: var(--hb-pier-edge); stroke-width: 2.5; fill: none; }
.harbor .berth-line.comb, .harbor .slip { stroke: var(--hb-pier-edge); stroke-width: 1.2;
                                          stroke-dasharray: 2 2; fill: none; }
.harbor .berth-line.guess { stroke-dasharray: 6 4; }
.harbor .berth-line.unverifiable { stroke: var(--hb-warning); stroke-width: 3.5; stroke-dasharray: 6 4; }
.harbor .berth-line.over { stroke: var(--hb-critical); stroke-width: 4; stroke-dasharray: none;
                           animation: hb-pulse 1.1s ease-in-out infinite; }
@keyframes hb-pulse { 50% { stroke-opacity: .25; } }
.harbor .flag.off { display: none; }
.harbor .flag circle { fill: var(--hb-critical); }
.harbor .flag text { fill: var(--hb-on-critical); font-size: 9px; font-weight: 800; text-anchor: middle; }
.harbor .flag.unverifiable circle { fill: var(--hb-warning); }
.harbor .flag.unverifiable text { fill: var(--hb-on-warning); }

/* Hulls and bands: a <g> whose CSS transform slides between "offshore" and "berthed". */
.harbor .hull { cursor: pointer; transition: transform .45s ease, opacity .45s ease; }
.harbor .hull.gone { opacity: 0; pointer-events: none; }
.harbor .hull .body { stroke: var(--hb-water); stroke-width: 1; }   /* a water ring between packed hulls */
.harbor .hull.planned .body { fill-opacity: .75; }
.harbor .hull.cancelled { opacity: .35; }
.harbor .hull.unknown .body { stroke: var(--hb-ink-2); stroke-width: 1.2; stroke-dasharray: 4 3; fill-opacity: .45; }
.harbor .hull:focus-visible { outline: none; }
.harbor .hull:focus-visible .body { stroke: var(--hb-ink); stroke-width: 2; }
.harbor .t-rv .body { fill: var(--hb-rv); }       .harbor .t-fv .body { fill: var(--hb-fv); }
.harbor .t-mv .body, .harbor .t-my .body { fill: var(--hb-motor); }
.harbor .t-sv .body, .harbor .t-sy .body { fill: var(--hb-sail); }
.harbor .t-barge .body { fill: var(--hb-barge); } .harbor .t-tug .body { fill: var(--hb-tug); }
.harbor .t-osv .body { fill: var(--hb-osv); }     .harbor .t-other .body { fill: var(--hb-other); }
.harbor .t-event .body { stroke: var(--hb-muted); stroke-dasharray: 3 2; }
.harbor .t-closure .body { stroke: var(--hb-muted); }
.harbor .stripes { display: none; }
.harbor .hull.over .stripes { display: block; }       /* striped overlay: the berth is over capacity */
.harbor .name { font-size: 10px; font-weight: 600; fill: var(--hb-ink); pointer-events: none;
                paint-order: stroke; stroke: var(--hb-water); stroke-width: 3px; stroke-linejoin: round; }
.harbor .badge rect { fill: var(--hb-critical); }
.harbor .badge text { fill: var(--hb-on-critical); font-size: 8.5px; font-weight: 700; }

/* Legend */
.harbor .legend-box { fill: var(--hb-surface); fill-opacity: .88; stroke: var(--hb-border); }
.harbor .legend text { fill: var(--hb-ink-2); font-size: 11px; }
.harbor .legend .line-over { stroke: var(--hb-critical); stroke-width: 4; }
.harbor .legend .line-unverifiable { stroke: var(--hb-warning); stroke-width: 3.5; stroke-dasharray: 6 4; }

@media (prefers-reduced-motion: reduce) {
  .harbor .hull { transition: none; }
  .harbor .berth-line.over { animation: none; }
}`;

/* ---- 2. Constants. Every distance is in feet (1 SVG unit = 1 ft). ---- */
const FT = {
  viewW: 600, viewH: 560, // the map; the container stretches it to its own width
  fender: 2,              // water between a hull's side and the berth face
  gap: 10,                // water between hulls packed end to end, when a berth has no clearance of its own
  nominal: 40,            // drawn length of a vessel whose length is unknown
  unnamed: 60,            // drawn length of an unknown berth whose length is unknown
  offshore: 90,           // how far out a hull waits before arriving / after departing
  band: 14,               // thickness of an event or closure band
};
const SLIDE_MS = 450;     // the CSS transition on .hull; departed hulls are removed after it
const NS = 'http://www.w3.org/2000/svg';
let instances = 0;        // gives each map its own pattern ids, so two maps on a page do not clash

/* Vessel type from the name's prefix: 'R/V Petrel' -> 'rv', 'OS/V Skua' -> 'osv', 'Sea Lark' -> 'other'. */
const PREFIX_RE = /^(R\/V|M\/V|F\/V|S\/V|M\/Y|S\/Y|OS\/V|OSV|Tug|Barge)\b/i;
const TYPE_NAME = { rv: 'Research vessel', mv: 'Motor vessel', fv: 'Fishing vessel', sv: 'Sailing vessel',
                    my: 'Motor yacht', sy: 'Sailing yacht', osv: 'Offshore supply vessel', tug: 'Tug',
                    barge: 'Barge', other: 'Other craft', event: 'Event', closure: 'Closure' };
function typeOf(occ) {
  if (occ.kind !== 'vessel') return occ.kind;
  const m = PREFIX_RE.exec(occ.name || '');
  return m ? m[1].toLowerCase().replace('/', '') : 'other';
}

/* ---- 3. Small helpers ---- */
function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function text(parent, attrs, content) {
  const t = el('text', attrs, parent);
  t.textContent = content;
  return t;
}
const feet = n => (n == null ? '?' : `${Math.round(n * 10) / 10}'`);   // 90 -> 90', null -> ?
const beamOf = L => Math.max(8, Math.min(36, L * 0.24));               // a plausible beam for a hull
const has = (set, id) => set.has(id) || set.has(String(id)) || set.has(Number(id));
function toSet(x) { return x instanceof Set ? x : new Set(x || []); }
function prettyDate(iso) {
  const d = new Date(iso + 'T00:00:00Z');
  return isNaN(d) ? String(iso) : d.toLocaleDateString(undefined,
    { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
}

/* Hull outline in local coordinates: centreline on y = 0, stern at x = -L/2 (a half
   circle), bow at x = +L/2 (pointed). h is half the beam. A band is a plain rectangle. */
function hullPath(L, h) {
  const s = -L / 2, e = L / 2, taper = Math.min(L * 0.3, 3 * h);
  return `M${s + h},${-h} H${e - taper} Q${e},${-h * 0.35} ${e},0 Q${e},${h * 0.35} ${e - taper},${h}` +
         ` H${s + h} A${h},${h} 0 0 1 ${s + h},${-h} Z`;
}
const bandPath = (L, h) => `M${-L / 2},${-h} h${L} v${2 * h} h${-L} Z`;

/* ---- 4. Where each named berth is on the map ----------------------------------------
   A linear place has:  start = the shore end of the face (feet);  dir = unit vector along
   the face, hulls pack in this direction;  water = unit vector from the face into open
   water, hulls sit on that side and arrive from it.  A comb (finger piers, small craft
   slips) has `slots` instead: one centreline per slip, each entered along dir.
   `decks` are the pier-coloured rectangles drawn for the structure. ---- */
function geometryOf(berths) {
  const named = name => berths.find(b => b.name === name);
  const len = (b, fallback) => (b && b.length_ft) || fallback;
  const pierLen = len(named('North Pier West'), 410), pierW = len(named('North Pier Face'), 75);
  return { shoreY: 30, pierX: 150, pierW, pierR: 150 + pierW, pierLen, faceY: 30 + pierLen };
}

/* A float moored off the south shore; its berth is the north edge, stem to the shore. */
function float(x, L) {
  return { start: [x, 500], dir: [1, 0], water: [0, -1],
           decks: [[x, 500, L, 10], [x + L / 2 - 3, 510, 6, 30]] };
}
/* A comb of n slips of slotLen feet, first centreline at (x, y0), fingers between them. */
function comb(x, y0, n, pitch, slotLen) {
  const slots = [], decks = [];
  for (let i = 0; i < n; i++) slots.push([x, y0 + pitch * i]);
  for (let i = 0; i <= n; i++) decks.push([x, y0 + pitch * i - pitch / 2 - 2, slotLen + 4, 4]);
  return { slots, slotLen, pitch, dir: [1, 0], water: [0, 0], decks };
}
const PLACES = {
  'North Pier West':  g => ({ start: [g.pierX, g.shoreY], dir: [0, 1], water: [-1, 0] }),
  'North Pier Face':  g => ({ start: [g.pierX, g.faceY], dir: [1, 0], water: [0, 1] }),
  'North Pier East':  (g, L) => ({ start: [g.pierR, g.faceY - L], dir: [0, 1], water: [1, 0] }),
  'Inner Channel':    () => ({ start: [40, 455], dir: [0, 1], water: [1, 0] }),
  'South Float West': (g, L) => float(300, L),
  'South Float East': (g, L) => float(420, L),
  'North Finger Piers': g => Object.assign(comb(g.pierR, 65, 4, 36, 36),
    { label: { x: g.pierR + 3, y: 37, anchor: 'start', lines: ['North Finger Piers (schematic)'] },
      flag: [g.pierR - 10, 37] }),
  'Small craft slips (institution boats)': () => {
    const c = comb(52, 331, 5, 22, 26);
    c.decks.push([40, 320, 12, 110]);                      // the float the fingers hang off
    return Object.assign(c, { label: { x: 20, y: 375, rotate: -90, lines: ['Small craft slips', '(institution boats)'] },
                              flag: [20, 300] });
  },
};

/* The place for one berth. Unknown names become floats stacked along the south shore,
   east of the named floats; `extra` is the running x position for them. */
function placeFor(b, g, extra) {
  const L = b.length_ft || FT.unnamed;
  const make = PLACES[b.name];
  let place;
  if (make) place = make(g, L);
  else {                                                   // unnamed: the next cell along the south shore,
    const cell = Math.max(L, (b.name.length + 10) * 5.5) + 20;   // wide enough for the float and its label
    place = float(extra.x + (cell - L) / 2, L);
    extra.x += cell;
  }
  place.len = L;
  place.guess = b.length_ft == null && !place.slots;   // drawn length is a placeholder
  if (!place.label) Object.assign(place, annotate(place, b));
  return place;
}

/* Label and flag-badge positions for a linear face: the label sits on the land side of
   the face's midpoint, reading along the face; the badge sits a little further inland. */
function annotate(place, b) {
  const [sx, sy] = place.start, [dx, dy] = place.dir, [wx, wy] = place.water;
  const mx = sx + dx * place.len / 2, my = sy + dy * place.len / 2;
  const name = b.length_ft == null ? `${b.name} - length?` : `${b.name} - ${feet(b.length_ft)}`;
  return { label: { x: mx - wx * 16, y: my - wy * 16, rotate: dx === 0 ? -90 : 0, lines: [name] },
           flag: [mx - wx * 30, my - wy * 30] };
}

/* ---- 5. Drawing the fixed parts: land, pier, berth faces, labels ---- */
function drawLand(view, g, viewW) {
  const land = view.layers.land;
  land.textContent = '';
  el('rect', { x: 0, y: 0, width: viewW, height: g.shoreY, class: 'land' }, land);
  el('rect', { x: 0, y: 0, width: 40, height: FT.viewH, class: 'land' }, land);
  el('rect', { x: 0, y: 540, width: viewW, height: 20, class: 'land' }, land);
  el('rect', { x: g.pierX, y: g.shoreY, width: g.pierW, height: g.pierLen, class: 'deck' }, land);
}

function drawBerth(view, b, place) {
  const { structures, faces, labels } = view.layers;
  for (const [x, y, w, h] of place.decks || []) el('rect', { x, y, width: w, height: h, class: 'deck' }, structures);
  let line;
  if (place.slots) {                                     // a comb: dashed slot boxes, one outline for the flags
    const n = place.slots.length, [x, y0] = place.slots[0], half = place.pitch / 2 - 3;
    for (const [sx, sy] of place.slots)
      el('rect', { x: sx, y: sy - half, width: place.slotLen, height: 2 * half, class: 'slip' }, structures);
    line = el('rect', { x: x - 1, y: y0 - place.pitch / 2 - 4, width: place.slotLen + 6,
                        height: place.pitch * n + 8, class: 'berth-line comb' }, faces);
  } else {
    const [x, y] = place.start, [dx, dy] = place.dir;
    line = el('line', { x1: x, y1: y, x2: x + dx * place.len, y2: y + dy * place.len,
                        class: 'berth-line' + (place.guess ? ' guess' : '') }, faces);
  }
  const title = el('title', {}, line);
  const lab = place.label;
  const t = text(labels, { class: 'lbl small', 'text-anchor': lab.anchor || 'middle', 'dominant-baseline': 'middle',
                           transform: `translate(${lab.x} ${lab.y}) rotate(${lab.rotate || 0})` }, lab.lines[0]);
  for (const extra of lab.lines.slice(1)) el('tspan', { x: 0, dy: 12 }, t).textContent = extra;
  const flag = el('g', { class: 'flag off', transform: `translate(${place.flag[0]} ${place.flag[1]})` }, labels);
  el('circle', { r: 6 }, flag);
  const flagText = text(flag, { y: 3.2 }, '!');
  view.berthEls.set(b.id, { line, title, flag, flagText });
}

const berthTitle = b => `${b.name} - ${b.length_ft == null ? 'length unknown' : feet(b.length_ft)}` +
                        ` - ${b.capacity_mode === 'exclusive' ? 'one occupant at a time' : 'shared end to end'}`;

/* The rules' verdict for a berth today: red pulse (over capacity) or amber dashes (a length
   is missing, so nobody can say). A badge with "!" or "?" repeats the colour as a symbol. */
function markBerth(view, b, F) {
  const e = view.berthEls.get(b.id);
  const over = has(F.overCapacity, b.id), unsure = !over && has(F.unverifiable, b.id);
  e.line.classList.toggle('over', over);
  e.line.classList.toggle('unverifiable', unsure);
  e.flag.setAttribute('class', 'flag ' + (over ? 'over' : unsure ? 'unverifiable' : 'off'));
  e.flagText.textContent = over ? '!' : '?';
  e.title.textContent = berthTitle(b) +
    (over ? ' - OVER CAPACITY today' : unsure ? ' - cannot verify today: a length is missing' : '');
}

/* ---- 6. Placing hulls ---- */
/* The face a hull ties up to: the berth's own face, or slot number `slot` of a comb. */
function faceOf(place, slot) {
  if (!place.slots) return place;
  return { start: place.slots[slot % place.slots.length], dir: place.dir, water: place.water };
}
const byArrival = (a, b) => String(a.start).localeCompare(String(b.start)) || (a.id < b.id ? -1 : 1);

/* Where each occupant goes along its berth. Vessels pack end to end from the shore end,
   earliest arrival nearest the shore, the berth's clearance of water between them; if they add up to
   more than the face, the last ones simply stick out past the end - that is the picture
   of an over-capacity day, but the verdict itself comes from the flags. Events and
   closures are bands across the whole berth (offset 0). On a comb, vessel k takes slot k. */
function layOut(occupants, place, gap = FT.gap) {
  const spots = [];
  let cursor = 0, k = 0;                                   // cursor: feet along the face; k: vessels so far
  for (const occ of occupants.slice().sort(byArrival)) {
    if (occ.kind !== 'vessel') { spots.push({ occ, offset: 0, slot: 0 }); continue; }
    if (place.slots) {
      const n = place.slots.length;                        // a full comb stacks the extras, 8 ft along
      spots.push({ occ, offset: 8 * Math.floor(k / n), slot: k % n });
    } else {
      spots.push({ occ, offset: cursor, slot: 0 });
      cursor += (occ.length_ft || FT.nominal) + gap;
    }
    k++;
  }
  return spots;
}

/* A hull's drawn size and resting place, in feet: length L, half-beam, centre (cx, cy),
   heading (0 = bow east, 90 = bow south), which local side the water is on (+1/-1), and
   the direction it arrives from (open water; for a slip, along the slip itself). */
function geometryFor(occ, place, offset, slot) {
  const band = occ.kind !== 'vessel', face = faceOf(place, slot);
  if (band && place.slots) {                               // a band over the whole comb
    const n = place.slots.length, [x, y0] = place.slots[0];
    return { L: place.slotLen, half: place.pitch * n / 2, cx: x + place.slotLen / 2,
             cy: y0 + place.pitch * (n - 1) / 2, angle: 0, side: 1, arrive: place.dir, band };
  }
  const L = band ? place.len : (occ.length_ft || FT.nominal);
  const half = band ? FT.band / 2 : beamOf(L) / 2;
  const along = offset + L / 2;                            // hull centre, measured along the face
  const out = place.slots ? 0 : FT.fender + half;          // pushed off the face onto the water side
  const [sx, sy] = face.start, [dx, dy] = face.dir, [wx, wy] = face.water;
  const inSlip = !wx && !wy;
  return { L, half, cx: sx + dx * along + wx * out, cy: sy + dy * along + wy * out,
           angle: Math.atan2(dy, dx) * 180 / Math.PI, side: dx * wy - dy * wx > 0 ? 1 : -1,
           arrive: inSlip ? [dx, dy] : [wx, wy], band };
}
/* The CSS transform for a hull at its berth, or parked FT.offshore feet out (where the
   arrival animation starts and the departure animation ends). */
function transformCss(geo, berthed) {
  const k = berthed ? 0 : FT.offshore;
  return `translate(${geo.cx + geo.arrive[0] * k}px, ${geo.cy + geo.arrive[1] * k}px) rotate(${geo.angle}deg)`;
}

/* One <g> per reservation id, kept in view.hulls so the same reservation keeps its element
   from day to day (that is what makes it slide rather than blink). A new one is born
   offshore; the browser must lay it out there before the berthed transform is set, or the
   slide-in would be skipped. */
function hullFor(view, occ, geo) {
  let g = view.hulls.get(occ.id);
  if (g) { g.classList.remove('gone'); return g; }
  g = el('g', { tabindex: 0, role: 'button' }, occ.kind === 'vessel' ? view.layers.hulls : view.layers.bands);
  g.style.transform = transformCss(geo, false);
  g.getBoundingClientRect();
  g.addEventListener('click', () => select(view, occ.id));
  g.addEventListener('keydown', ev => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(view, occ.id); }
  });
  view.hulls.set(occ.id, g);
  return g;
}
function select(view, id) {
  const occ = view.occupants.get(id);
  if (occ && view.onSelect) view.onSelect(occ);
}

/* Redraw a hull's shape, colour, label, flags and hover text for today. */
function paintHull(view, g, occ, b, geo, F) {
  const type = typeOf(occ);
  // "unknown" is a fact about the vessel (no length on file), never a flag from the rules
  const unknown = occ.kind === 'vessel' && occ.length_ft == null;
  const over = has(F.overCapacity, b.id);
  // Overhang in feet, for a flagged misfit whose two lengths are known: drawing arithmetic, not a rule.
  const misfit = has(F.misfits, occ.id) && occ.length_ft != null && b.length_ft != null;
  const overhang = misfit ? Math.max(0, occ.length_ft - b.length_ft) : 0;
  const hover = hoverText(occ, b, type, unknown, over, overhang);
  g.setAttribute('class', `hull t-${type} ${occ.status || ''}${unknown ? ' unknown' : ''}${over ? ' over' : ''}`);
  g.setAttribute('aria-label', hover);
  g.textContent = '';                                      // rebuild the children (cheap: five elements)
  const shape = geo.band ? bandPath(geo.L, geo.half) : hullPath(geo.L, geo.half);
  const body = el('path', { d: shape, class: 'body' }, g);
  if (geo.band) body.setAttribute('fill', `url(#${view.ids[occ.kind]})`);
  el('path', { d: shape, class: 'stripes', fill: `url(#${view.ids.stripes})` }, g);
  el('title', {}, g).textContent = hover;

  // Name: inside the hull when it is long enough, otherwise beside it on the water side.
  const vertical = geo.angle % 180 !== 0;
  // the dashed hull and the hover text say "length unknown"; the label stays short so it fits the map
  const label = occ.kind === 'closure' ? `closed - ${occ.name}` : occ.name;
  const inside = geo.L >= String(label).length * 6 + 16;
  const ty = inside ? 0 : geo.side * (geo.half + 8);
  const t = text(g, { class: 'name', 'dominant-baseline': 'middle', y: ty,
                      x: inside || vertical ? 0 : -geo.L / 2 + 2,
                      'text-anchor': inside || vertical ? 'middle' : 'start' }, label);
  if (vertical) t.setAttribute('transform', `rotate(180 0 ${ty})`);   // so it reads bottom-to-top, in place

  // "+NN ft" badge for a vessel longer than its berth, sitting over the part that sticks out.
  if (overhang > 0) {
    const badge = el('g', { class: 'badge', transform:
      `translate(${geo.L / 2 - overhang / 2},${-geo.side * (geo.half + 8)})${vertical ? ' rotate(180)' : ''}` }, g);
    el('rect', { x: -18, y: -6, width: 36, height: 12, rx: 3 }, badge);
    text(badge, { 'text-anchor': 'middle', 'dominant-baseline': 'middle', y: 0.5 }, `+${Math.round(overhang)} ft`);
  }
}
function hoverText(occ, b, type, unknown, over, overhang) {
  const parts = [occ.name, TYPE_NAME[type] || type];
  if (occ.kind === 'vessel') parts.push(unknown ? 'length unknown' : `${feet(occ.length_ft)} long`, `at ${b.name}`);
  else parts.push(`takes the whole of ${b.name}`);
  if (occ.start) parts.push(`${occ.start} to ${occ.end}`);
  if (occ.status && occ.status !== 'confirmed') parts.push(occ.status);
  if (overhang > 0) parts.push(`${Math.round(overhang)} ft longer than the berth`);
  if (over) parts.push('berth over capacity');
  return parts.join(' - ');
}

/* A hull that is not here today slides back out to sea, then leaves the DOM. */
function retire(view, id, g) {
  if (g.classList.contains('gone')) return;
  g.classList.add('gone');
  g.style.transform = g.getAttribute('data-offshore');
  const t = setTimeout(() => {
    view.timers.delete(t);
    if (g.classList.contains('gone')) { g.remove(); view.hulls.delete(id); view.occupants.delete(id); }
  }, SLIDE_MS + 100);
  view.timers.add(t);
}

/* ---- 7. One day: put every occupant on its berth, colour the verdicts, retire the rest ---- */
function setDay(view, dayIso, occupantsByBerthId, flags) {
  const F = normalFlags(flags), byBerth = occupantsByBerthId || {};
  view.dateText.textContent = prettyDate(dayIso);
  const seen = new Set();
  for (const b of view.berths) {
    const place = view.places.get(b.id);
    markBerth(view, b, F);
    for (const { occ, offset, slot } of layOut(byBerth[b.id] || [], place, b.clearance_ft != null ? b.clearance_ft : FT.gap)) {
      const geo = geometryFor(occ, place, offset, slot);
      const g = hullFor(view, occ, geo);
      view.occupants.set(occ.id, occ);
      seen.add(occ.id);
      paintHull(view, g, occ, b, geo, F);
      g.setAttribute('data-offshore', transformCss(geo, false));
      g.style.transform = transformCss(geo, true);
    }
  }
  for (const [id, g] of view.hulls) if (!seen.has(id)) retire(view, id, g);
}
function normalFlags(flags) {
  const f = flags || {};
  return { overCapacity: toSet(f.overCapacity), unverifiable: toSet(f.unverifiable),
           misfits: toSet(f.misfits), unknownLength: toSet(f.unknownLength) }; // unknownLength: vessels with no length on file
}

/* ---- 8. The berths: place each one, size the map, draw land, structures and faces ---- */
function setBerths(view, berths) {
  view.berths = berths.slice();
  view.places = new Map();
  view.berthEls = new Map();
  for (const name of ['structures', 'faces', 'labels', 'bands', 'hulls']) view.layers[name].textContent = '';
  view.hulls.clear();
  view.occupants.clear();
  const g = geometryOf(berths), extra = { x: 540 };        // unnamed berths start east of the named floats
  for (const b of berths) view.places.set(b.id, placeFor(b, g, extra));
  const viewW = Math.max(FT.viewW, extra.x + 10);          // widen the map if they ran past the edge
  view.svg.setAttribute('viewBox', `0 0 ${viewW} ${FT.viewH}`);
  drawLand(view, g, viewW);
  for (const b of berths) drawBerth(view, b, view.places.get(b.id));
}

/* ---- 9. Fixed chrome: hatch patterns, the 100 ft scale bar (a 100-unit line - that IS
   the scale), a north arrow, the date, and the legend ---- */
function drawDefs(view) {
  const defs = el('defs', {}, view.svg);
  const pattern = (id, size, angle) => el('pattern', { id, patternUnits: 'userSpaceOnUse', width: size,
                                                        height: size, patternTransform: `rotate(${angle})` }, defs);
  let p = pattern(view.ids.event, 8, 45);                  // event: diagonal hatch
  el('rect', { width: 8, height: 8, class: 'hatch-bg' }, p);
  el('line', { x1: 0, y1: 0, x2: 0, y2: 8, class: 'hatch-line' }, p);
  p = pattern(view.ids.closure, 8, 45);                    // closure: grey cross-hatch
  el('rect', { width: 8, height: 8, class: 'hatch-bg' }, p);
  el('line', { x1: 0, y1: 0, x2: 0, y2: 8, class: 'hatch-grey' }, p);
  el('line', { x1: 0, y1: 0, x2: 8, y2: 0, class: 'hatch-grey' }, p);
  p = pattern(view.ids.stripes, 6, 135);                   // over capacity: red stripes over the hull
  el('line', { x1: 0, y1: 0, x2: 0, y2: 6, class: 'stripe-line' }, p);
}
function drawChrome(view) {
  const c = el('g', { class: 'chrome' }, view.svg);
  const bar = el('g', { transform: 'translate(470 62)' }, c);
  el('line', { x1: 0, y1: 0, x2: 100, y2: 0 }, bar);
  el('line', { x1: 0, y1: -4, x2: 0, y2: 4 }, bar);
  el('line', { x1: 100, y1: -4, x2: 100, y2: 4 }, bar);
  text(bar, { class: 'lbl small', x: 50, y: -7, 'text-anchor': 'middle' }, '100 ft');
  const north = el('g', { transform: 'translate(575 100)' }, c);
  el('line', { x1: 0, y1: 0, x2: 0, y2: -24 }, north);
  el('path', { d: 'M-4,-18 L0,-26 L4,-18' }, north);
  text(north, { class: 'lbl small', y: 11, 'text-anchor': 'middle' }, 'N');
  text(c, { class: 'lbl small', x: 560, y: 20, 'text-anchor': 'end' }, 'SHORE');
  view.dateText = text(c, { class: 'lbl', x: 8, y: 20 }, '');
}

const LEGEND = [
  ['hull t-rv', 'R/V research'], ['hull t-mv', 'M/V, M/Y motor'], ['hull t-fv', 'F/V fishing'],
  ['hull t-sv', 'S/V, S/Y sail'], ['hull t-barge', 'Barge'], ['hull t-tug', 'Tug'],
  ['hull t-osv', 'OSV supply'], ['hull t-other', 'Other craft'],
  ['band event', 'Event (takes the whole berth)'], ['band closure', 'Closure (takes the whole berth)'],
  ['hull t-rv over', 'Berth over capacity (red, pulsing)'], ['line-unverifiable', 'Cannot verify: a length is missing'],
  ['hull t-rv unknown', 'Length unknown (drawn as 40 ft)'], ['badge', 'Longer than its berth'],
];
function drawLegend(view) {
  const box = el('g', { class: 'legend', transform: 'translate(340 128)' }, view.svg);
  el('rect', { x: 0, y: 0, width: 250, height: LEGEND.length * 19 + 14, rx: 8, class: 'legend-box' }, box);
  LEGEND.forEach(([kind, label], i) => {
    const row = el('g', { transform: `translate(28 ${19 * i + 17})` }, box);
    swatch(view, row, kind);
    text(row, { x: 22, 'dominant-baseline': 'middle' }, label);
  });
}
function swatch(view, row, kind) {
  if (kind === 'line-unverifiable') return el('line', { x1: -14, y1: 0, x2: 14, y2: 0, class: kind }, row);
  if (kind === 'badge') {
    const b = el('g', { class: 'badge' }, row);
    el('rect', { x: -16, y: -6, width: 32, height: 12, rx: 3 }, b);
    return text(b, { 'text-anchor': 'middle', 'dominant-baseline': 'middle', y: 0.5 }, '+NN ft');
  }
  const band = kind.startsWith('band'), what = kind.split(' ')[1];
  const g = el('g', { class: band ? `hull t-${what}` : kind }, row);
  const d = band ? bandPath(28, 5) : hullPath(28, 5);
  const body = el('path', { d, class: 'body' }, g);
  if (band) body.setAttribute('fill', `url(#${view.ids[what]})`);
  if (kind.includes('over')) el('path', { d, class: 'stripes', fill: `url(#${view.ids.stripes})` }, g);
  return g;
}

/* ---- 10. Public API ---- */
function create(container, opts) {
  if (!document.getElementById('harbor-style')) {
    const style = document.createElement('style');
    style.id = 'harbor-style';
    style.textContent = CSS;
    document.head.appendChild(style);
  }
  const n = ++instances;
  const view = { container, onSelect: (opts && opts.onSelect) || null, berths: [], places: new Map(),
                 berthEls: new Map(), hulls: new Map(), occupants: new Map(), timers: new Set(), layers: {},
                 ids: { event: `hb${n}-event`, closure: `hb${n}-closure`, stripes: `hb${n}-stripes` } };
  container.classList.add('harbor');
  view.map = document.createElement('div');
  view.map.className = 'harbor-map';
  container.appendChild(view.map);
  // role="group", not "img": an image's children are presentational, and the hulls inside are buttons
  view.svg = el('svg', { class: 'harbor-svg', viewBox: `0 0 ${FT.viewW} ${FT.viewH}`, role: 'group',
                         'aria-label': 'Plan view of the waterfront berths' }, view.map);
  drawDefs(view);
  for (const name of ['land', 'structures', 'faces', 'labels', 'bands', 'hulls'])
    view.layers[name] = el('g', { class: `layer-${name}` }, view.svg);
  drawChrome(view);
  drawLegend(view);
  return {
    setBerths: berths => setBerths(view, berths || []),
    setDay: (dayIso, occupantsByBerthId, flags) => setDay(view, dayIso, occupantsByBerthId, flags),
    destroy: () => destroy(view),
    svg: view.svg,                                         // handy for tests and debugging
  };
}
function destroy(view) {
  for (const t of view.timers) clearTimeout(t);
  view.timers.clear();
  view.hulls.clear();
  view.occupants.clear();
  view.map.remove();
  view.container.classList.remove('harbor');
}

window.Harbor = { create };
})();
