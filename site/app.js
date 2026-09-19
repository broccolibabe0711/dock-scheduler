/* Dock Scheduler front end.
 *
 * Renders what the API (or, on GitHub Pages, the exported JSON snapshot)
 * says. It never decides whether a booking is allowed: verdicts and findings
 * come from dock/rules.py through the API, and the snapshot carries the
 * flags the audit computed. The only arithmetic here is for drawing.
 */
(() => {
  'use strict';

  // ---------------------------------------------------------------- helpers
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const pad = (n) => String(n).padStart(2, '0');
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const VIEWS = ['harbor', 'grid', 'book', 'registry', 'audit', 'issues'];

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined) continue;
      node.append(child.nodeType ? child : document.createTextNode(child));
    }
    return node;
  }
  const fmtFt = (n) => (n === null || n === undefined ? '?' : `${Number.isInteger(n) ? n : Number(n).toFixed(1)}'`);
  // All date arithmetic is on ISO day strings in UTC, so the viewer's time zone never shifts a day.
  const addDays = (iso, n) => { const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const daysInMonth = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate(); // m is 1-12
  const monthRange = (ym) => { const [y, m] = ym.split('-').map(Number); const n = daysInMonth(y, m); return { y, m, n, start: `${ym}-01`, end: `${ym}-${pad(n)}` }; };
  const isMonth = (ym) => /^\d{4}-(0[1-9]|1[0-2])$/.test(ym || '');
  const weekday = (iso) => 'SMTWTFS'[new Date(`${iso}T00:00:00Z`).getUTCDay()];
  const dayOf = (iso, ym) => (iso.slice(0, 7) === ym ? Number(iso.slice(8)) : (iso < ym ? -1e9 : 1e9));
  // Identity of a vessel name, the same folding dock/models.py name_key() does: not a rule, a key.
  const nameKey = (s) => (s || '').toLowerCase().replace(/\//g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  function prefixClass(name) {
    const m = /^(r\/v|m\/v|f\/v|s\/v|m\/y|s\/y|os\/v|osv|tug|barge)\b/i.exec(name || '');
    return m ? `t-${m[1].toLowerCase().replace('/', '')}` : 't-other';
  }
  const post = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const patch = (body) => ({ method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

  // ---------------------------------------------------------------- data layer
  // Same calls in both modes; the static mode answers from data/*.json.
  const Data = {
    mode: 'api',
    meta: null,
    cache: {},
    async init() {
      let response = null;
      try { response = await fetch('api/meta'); } catch (err) { response = null; } // network error: no server at all
      if (response && response.ok) {
        this.meta = await response.json();
        this.mode = 'api';
      } else if (response === null || response.status === 404) {
        this.mode = 'static';
        await this.loadStatic();
      } else {
        throw new Error(`the API answered ${response.status} ${response.statusText}`);
      }
      return this.meta;
    },
    async loadStatic() {
      const get = async (name) => {
        const r = await fetch(`data/${name}.json`);
        if (!r.ok) throw new Error(`data/${name}.json is missing (${r.status})`);
        return r.json();
      };
      const [meta, berths, vessels, reservations, issues, audit, flags] = await Promise.all(
        ['meta', 'berths', 'vessels', 'reservations', 'issues', 'audit', 'flags'].map(get));
      this.meta = meta;
      this.static = {
        berths, vessels, reservations, issues, audit,
        flags: {
          misfits: new Set(flags.misfits),
          unknown: new Set(flags.unknown_length),
          over: new Set(flags.over_capacity_days.map((x) => `${x.berth_id}|${x.day}`)),
          unverifiable: new Set(flags.unverifiable_days.map((x) => `${x.berth_id}|${x.day}`)),
        },
      };
    },
    async json(url, opts) {
      const r = await fetch(url, opts);
      const body = await r.json().catch(() => null);
      if (!r.ok) { const e = new Error(`${r.status} ${r.statusText}`); e.status = r.status; e.body = body; throw e; }
      return body;
    },
    async berths() {
      if (this.mode === 'static') return this.static.berths;
      if (!this.cache.berths) this.cache.berths = await this.json('api/berths');
      return this.cache.berths;
    },
    async vessels(q, limit = 50) {
      if (this.mode === 'static') { const k = nameKey(q); return this.static.vessels.filter((v) => nameKey(v.name).includes(k)).sort((a, b) => a.name.localeCompare(b.name)).slice(0, limit); }
      return this.json(`api/vessels?q=${encodeURIComponent(q)}&limit=${limit}`);
    },
    async reservations(start, end, includeCancelled = false) {
      if (this.mode === 'static') {
        return this.static.reservations.filter((r) => r.start <= end && r.end >= start && (includeCancelled || r.status !== 'cancelled'));
      }
      return this.json(`api/reservations?start=${start}&end=${end}${includeCancelled ? '&include_cancelled=true' : ''}`);
    },
    async loads(start, end) {
      if (this.mode === 'static') return this.staticLoads(start, end);
      return this.json(`api/loads?start=${start}&end=${end}`);
    },
    // The snapshot has no API to ask, so occupancy per day is assembled here from the
    // reservations. The feet each stay occupies were computed by the Python model and
    // exported; the conflict flags come from the audit. Nothing is judged here.
    staticLoads(start, end) {
      const { berths, flags } = this.static;
      const inRange = this.static.reservations.filter((r) => r.start <= end && r.end >= start && r.status !== 'cancelled');
      const out = [];
      for (const b of berths) {
        for (let day = start; day <= end; day = addDays(day, 1)) {
          const occupants = inRange.filter((r) => r.berth_id === b.id && r.start <= day && r.end >= day)
            .map((r) => ({ ...r, fit: flags.misfits.has(r.id) ? 'misfit' : (flags.unknown.has(r.id) ? 'unknown' : 'ok') }));
          let known = 0, unknown = 0;
          for (const o of occupants) {
            if (o.occupied_ft === null || o.occupied_ft === undefined) unknown++;
            else known += o.occupied_ft;
          }
          out.push({
            berth_id: b.id, day, known_ft: known, unknown_count: unknown, used_ft: unknown ? null : known,
            capacity_ft: b.length_ft,
            over_capacity: flags.over.has(`${b.id}|${day}`), unverifiable: flags.unverifiable.has(`${b.id}|${day}`), occupants,
          });
        }
      }
      return out;
    },
    async audit() { return this.mode === 'static' ? this.static.audit : this.json('api/audit'); },
    async issues(kind) {
      if (this.mode === 'static') { const all = this.static.issues; return { counts: all.counts, issues: kind ? all.issues.filter((i) => i.kind === kind) : all.issues }; }
      return this.json(`api/issues?limit=2000${kind ? `&kind=${encodeURIComponent(kind)}` : ''}`);
    },
    requireApi() { if (this.mode !== 'api') throw new Error('Booking needs the app running locally; this page is a read-only snapshot.'); },
    async check(body) { this.requireApi(); return this.json('api/check', post(body)); },
    async book(body) { this.requireApi(); return this.json('api/reservations', post(body)); },
    async suggest(params) { this.requireApi(); return this.json(`api/suggest?${new URLSearchParams(params)}`); },
    async patchReservation(id, body) { this.requireApi(); return this.json(`api/reservations/${id}`, patch(body)); },
    async createVessel(body) { this.requireApi(); return this.json('api/vessels', post(body)); },
    async patchVessel(id, body) { this.requireApi(); return this.json(`api/vessels/${id}`, patch(body)); },
  };

  // An occupant as the harbor module and the detail dialog want it, whichever mode produced it.
  const occupantOf = (o) => ({
    ...o, fit: o.fit || 'ok',
    length_ft: o.length_ft !== undefined ? o.length_ft : (o.vessel ? o.vessel.length_ft : null),
  });

  // ---------------------------------------------------------------- state and navigation
  const state = {
    berths: [], month: null, day: null, timer: null, harbor: null, loadsByMonth: new Map(),
    vessel: null, vesselHits: [], vesselSeq: 0,
  };

  const currentView = () => ($$('.tabs button').find((b) => b.getAttribute('aria-selected') === 'true') || { dataset: {} }).dataset.view || 'harbor';

  function showView(name) {
    if (!VIEWS.includes(name)) name = 'harbor';
    if (name !== 'harbor') stopPlaying();
    $$('.tabs button').forEach((b) => {
      const on = b.dataset.view === name;
      b.setAttribute('aria-selected', String(on));
      b.tabIndex = on ? 0 : -1;
    });
    $$('.view').forEach((v) => { v.hidden = v.id !== `view-${name}`; });
    if (location.hash !== `#${name}`) history.replaceState(null, '', `#${name}`);
    if (name === 'grid') renderGrid();
    if (name === 'harbor') renderHarbor();
    if (name === 'registry') renderRegistry();
    if (name === 'audit') renderAudit();
    if (name === 'issues') renderIssues();
  }

  function loadsForMonth(ym) {
    // the promise is cached, not the value, so two callers racing for one month share one fetch
    if (!state.loadsByMonth.has(ym)) {
      const { start, end } = monthRange(ym);
      const promise = Data.loads(start, end).catch((err) => { state.loadsByMonth.delete(ym); throw err; });
      state.loadsByMonth.set(ym, promise);
    }
    return state.loadsByMonth.get(ym);
  }
  const forgetLoads = () => state.loadsByMonth.clear();

  const failed = (host, err) => host.replaceChildren(el('div', { class: 'empty', text: `Could not load: ${err.message || err}` }));

  // ---------------------------------------------------------------- grid view
  async function renderGrid() {
    const ym = state.month;
    const { y, m, n, start, end } = monthRange(ym);
    $('#grid-month').value = ym;
    const grid = $('#grid');
    grid.replaceChildren(el('div', { class: 'empty', text: 'Loading…' }));
    let reservations, loads;
    try { [reservations, loads] = await Promise.all([Data.reservations(start, end, true), loadsForMonth(ym)]); }
    catch (err) { failed(grid, err); return; }
    if (ym !== state.month) return; // the user moved on while this month was loading
    const loadIndex = new Map(loads.map((l) => [`${l.berth_id}|${l.day}`, l]));
    const fitIndex = new Map();
    for (const l of loads) for (const o of l.occupants) fitIndex.set(o.id, o.fit);

    const gridTable = el('div', { class: 'grid-table', style: `--days:${n}` });
    const head = el('div', { class: 'grid-head' }, el('div', { text: `${MONTHS[m - 1]} ${y}` }));
    for (let d = 1; d <= n; d++) {
      const w = weekday(`${ym}-${pad(d)}`);
      head.append(el('div', { class: `day${w === 'S' ? ' weekend' : ''}`, text: `${w}\n${d}` }));
    }
    gridTable.append(head);

    let flagged = 0;
    for (const b of state.berths) {
      const row = el('div', { class: 'grid-row' });
      row.append(el('div', { class: 'label' }, b.name, el('small', { text: b.length_ft ? `${fmtFt(b.length_ft)} · ${b.capacity_mode}` : `${b.capacity_mode}, length unknown` })));
      const lanes = el('div', { class: 'lanes' });
      const cells = el('div', { class: 'cells' });
      for (let d = 1; d <= n; d++) {
        const iso = `${ym}-${pad(d)}`;
        const l = loadIndex.get(`${b.id}|${iso}`);
        if (l && (l.over_capacity || l.unverifiable)) flagged++;
        const open = () => startBooking(b, iso);
        cells.append(el('div', {
          class: `cell${l && l.over_capacity ? ' over' : ''}${l && l.unverifiable ? ' unverifiable' : ''}`,
          role: 'button', tabindex: '0', 'aria-label': `${b.name}, ${iso}: book here`,
          title: l ? loadTitle(l, b) : '', onclick: open,
          onkeydown: (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); } },
        }));
      }
      const bars = el('div', { class: 'bars' });
      const mine = reservations.filter((r) => r.berth_id === b.id)
        .sort((a, c) => a.start.localeCompare(c.start) || (a.id || 0) - (c.id || 0));
      const laneEnds = [];
      for (const r of mine) {
        let lane = laneEnds.findIndex((e) => e < r.start);
        if (lane < 0) { lane = laneEnds.length; laneEnds.push(r.end); } else laneEnds[lane] = r.end;
        const s = Math.max(1, dayOf(r.start, ym)), e = Math.min(n, dayOf(r.end, ym));
        const fit = fitIndex.get(r.id) || 'ok';
        bars.append(el('button', {
          type: 'button',
          class: `bar ${r.kind === 'vessel' ? prefixClass(r.name) : r.kind}${fit === 'misfit' ? ' misfit' : ''}${fit === 'unknown' ? ' unknown' : ''}${r.status === 'cancelled' ? ' cancelled' : ''}`,
          style: `grid-column:${s} / ${e + 1};grid-row:${lane + 1}`, title: `${r.name} ${r.start}..${r.end}`, text: r.name,
          onclick: (ev) => { ev.stopPropagation(); showDetail(r); },
        }));
      }
      lanes.append(cells, bars);
      row.append(lanes);
      gridTable.append(row);
    }
    grid.replaceChildren(gridTable);
    $('#grid-status').textContent = `${MONTHS[m - 1]} ${y}: ${reservations.length} reservation(s), ${flagged} flagged berth-day(s).`;
    renderLegend();
  }

  function loadTitle(l, b) {
    if (!l.occupants.length) return `${b.name}: free`;
    const names = l.occupants.map((o) => o.name).join(', ');
    if (l.over_capacity) return `${b.name} over capacity: ${names}`;
    if (l.unverifiable) return `${b.name}: ${names} (a length is missing, cannot verify)`;
    // feet used only matter when the berth is shared; a lone vessel is a fit question
    const shared = l.occupants.length > 1 && l.used_ft !== null && l.capacity_ft;
    return `${b.name}: ${names}${shared ? ` (${fmtFt(l.used_ft)} of ${fmtFt(l.capacity_ft)} with clearance)` : ''}`;
  }

  function renderLegend() {
    const items = [['t-rv', 'R/V research'], ['t-mv', 'M/V motor'], ['t-fv', 'F/V fishing'], ['t-sv', 'S/V sail'], ['t-my', 'M/Y yacht'], ['t-osv', 'OSV'], ['t-tug', 'Tug'], ['t-barge', 'Barge'], ['event', 'event (whole berth)'], ['closure', 'closure']];
    const legend = $('#grid-legend');
    legend.replaceChildren(...items.map(([cls, label]) => el('span', {}, el('i', { class: `swatch bar ${cls}` }), label)),
      el('span', {}, el('i', { class: 'swatch', style: 'box-shadow: inset 0 -3px 0 var(--bad)' }), 'day over capacity'),
      el('span', {}, el('i', { class: 'swatch', style: 'box-shadow: inset 0 -3px 0 var(--unknown)' }), 'shared, a length missing'),
      el('span', {}, el('i', { class: 'swatch bar', style: 'border:2px solid var(--bad);background:none' }), 'vessel longer than berth'));
  }

  // ---------------------------------------------------------------- booking view
  function startBooking(berth, iso) {
    $('#book-berth').value = berth.id;
    $('#book-start').value = iso;
    $('#book-end').value = iso;
    showView('book');
    const target = $('#book-kind').value === 'vessel' ? $('#book-vessel') : $('#book-title');
    target.focus();
  }

  function kindChanged() {
    const kind = $('#book-kind').value;
    $$('.vessel-only').forEach((n) => { n.hidden = kind !== 'vessel'; });
    $$('.non-vessel-only').forEach((n) => { n.hidden = kind === 'vessel'; });
    $('#book-vessel').required = kind === 'vessel';
  }

  let vesselSearchTimer = null;
  function vesselTyped() {
    const q = $('#book-vessel').value.trim();
    clearTimeout(vesselSearchTimer);
    vesselSearchTimer = setTimeout(async () => {
      const seq = ++state.vesselSeq; // a slow, older search must not overwrite a newer one
      let hits = [];
      try { hits = q ? await Data.vessels(q) : []; }
      catch (err) {
        if (seq === state.vesselSeq) { $('#vessel-facts').hidden = false; $('#vessel-summary').textContent = `Could not reach the vessel registry: ${errorText(err)}`; }
        return; // keep the previous hits; nothing is concluded from a failed search
      }
      if (seq !== state.vesselSeq) return;
      state.vesselHits = hits;
      $('#vessel-options').replaceChildren(...hits.map((v) => el('option', { value: v.name, text: v.length_ft ? fmtFt(v.length_ft) : 'length unknown' })));
      vesselChosen();
    }, 150);
  }

  function vesselChosen() {
    const typed = $('#book-vessel').value.trim();
    const key = nameKey(typed);
    state.vessel = key ? state.vesselHits.find((v) => nameKey(v.name) === key) || null : null;
    const facts = $('#vessel-facts');
    facts.hidden = !typed;
    if (!typed) return;
    if (state.vessel) {
      $('#vessel-summary').textContent = state.vessel.length_ft
        ? `${state.vessel.name}: ${fmtFt(state.vessel.length_ft)}${state.vessel.operator ? `, ${state.vessel.operator}` : ''}${state.vessel.rafts_ok ? ', will raft alongside' : ''}`
        : `${state.vessel.name}: length not on file. The referee will answer UNKNOWN until it is entered.`;
      $('#vessel-length-wrap').hidden = !!state.vessel.length_ft;
    } else {
      $('#vessel-summary').textContent = `"${typed}" is not in the registry. Pick a name from the list, or enter its length and press "Save length" to add it.`;
      $('#vessel-length-wrap').hidden = false;
    }
  }

  async function saveVesselLength() {
    const ft = Number($('#vessel-length').value);
    if (!(ft > 0)) { $('#vessel-summary').textContent = 'Enter the length overall in feet first.'; return; }
    try {
      if (state.vessel) state.vessel = await Data.patchVessel(state.vessel.id, { length_ft: ft });
      else state.vessel = await Data.createVessel({ name: $('#book-vessel').value.trim(), length_ft: ft });
      state.vesselHits = [state.vessel];
      $('#book-vessel').value = state.vessel.name;
      forgetLoads();
      vesselChosen();
    } catch (err) { showError(err); }
  }

  // The vessel a booking is about. Check and Suggest never create anything; only
  // Save may add a vessel that is not in the registry yet (with the length typed, if any).
  async function bookingVessel(mayCreate) {
    if ($('#book-kind').value !== 'vessel') return null;
    const typed = $('#book-vessel').value.trim();
    if (!typed) throw new Error('Choose or type a vessel name.');
    if (state.vessel && nameKey(state.vessel.name) === nameKey(typed)) return state.vessel;
    const hit = state.vesselHits.find((v) => nameKey(v.name) === nameKey(typed));
    if (hit) { state.vessel = hit; return hit; }
    if (!mayCreate) throw new Error(`"${typed}" is not in the registry. Pick it from the list, or add it with "Save length"; Save booking can also add it.`);
    const ft = Number($('#vessel-length').value) || null;
    state.vessel = await Data.createVessel({ name: typed, length_ft: ft });
    state.vesselHits = [state.vessel];
    vesselChosen();
    return state.vessel;
  }

  async function bookingBody(mayCreate) {
    const vessel = await bookingVessel(mayCreate);
    return {
      berth_id: Number($('#book-berth').value), kind: $('#book-kind').value, vessel_id: vessel ? vessel.id : null,
      title: $('#book-title').value.trim(), start: $('#book-start').value, end: $('#book-end').value,
      notes: $('#book-notes').value.trim(), override_reason: $('#book-override').value.trim() || null,
    };
  }

  function renderResult(result, lead) {
    const box = $('#book-result');
    const verdictText = { ok: 'OK: every rule passed with real numbers.', conflict: 'CONFLICT: the booking breaks a rule.', unknown: 'UNKNOWN: a length the rules need is missing.' }[result.verdict] || result.verdict;
    box.replaceChildren(
      lead ? el('p', { text: lead }) : null,
      el('div', { class: `verdict ${result.verdict}`, text: verdictText }),
      el('ul', { class: 'findings' }, ...result.findings.map((f) => el('li', { class: f.severity },
        el('div', { class: 'code', text: `${f.severity} · ${f.code.replace(/_/g, ' ')}${f.day ? ` · ${f.day}` : ''}` }),
        el('div', { text: f.message })))));
    $('#override-wrap').hidden = !result.blocking;
  }

  function errorText(err) {
    const detail = err.body && err.body.detail;
    if (Array.isArray(detail)) { // FastAPI request validation: say which field
      return detail.map((d) => `${(d.loc || []).filter((x) => x !== 'body').join('.')}: ${d.msg}`).join('; ');
    }
    if (typeof detail === 'string') return detail;
    return err.message || String(err);
  }

  function showError(err) {
    const detail = err.body && err.body.detail;
    if (detail && detail.findings) { renderResult(detail, 'Not saved.'); return; }
    $('#book-result').replaceChildren(el('div', { class: 'verdict conflict', text: errorText(err) }));
  }

  async function checkBooking() {
    try { renderResult(await Data.check(await bookingBody(false)), 'Checked, not saved:'); $('#book-suggestions').replaceChildren(); }
    catch (err) { showError(err); }
  }

  async function saveBooking(ev) {
    ev.preventDefault();
    try {
      const body = await bookingBody(true);
      const out = await Data.book(body);
      forgetLoads();
      renderResult(out.check, `Saved as reservation #${out.reservation.id} (${out.reservation.start}..${out.reservation.end}).`);
      $('#book-override').value = '';
      $('#book-result').append(el('p', {}, el('button', { type: 'button', text: 'See it in the grid', onclick: () => { state.month = out.reservation.start.slice(0, 7); showView('grid'); } })));
    } catch (err) { showError(err); }
  }

  async function suggestBerths() {
    try {
      const body = await bookingBody(false);
      const params = { start: body.start, end: body.end, kind: body.kind, title: body.title || 'requested booking', include_unknown: 'true' };
      if (body.vessel_id) params.vessel_id = body.vessel_id;
      const out = await Data.suggest(params);
      const box = $('#book-suggestions');
      if (!out.length) { box.replaceChildren(el('p', { class: 'empty', text: 'No berth is free for those dates without a conflict.' })); return; }
      box.replaceChildren(el('h3', { text: 'Where it could go, smallest fitting berth first' }), ...out.map((s) => el('div', { class: 'suggestion' },
        el('div', {}, el('strong', { text: s.berth.name }), ` ${s.berth.length_ft ? fmtFt(s.berth.length_ft) : 'length unknown'} · ${s.check.verdict.toUpperCase()}`,
          s.check.findings.length ? el('div', { class: 'hint', text: s.check.findings.map((f) => f.message).join(' ') }) : null),
        el('button', { type: 'button', text: 'Use this berth', onclick: () => { $('#book-berth').value = s.berth.id; checkBooking(); } }))));
    } catch (err) { showError(err); }
  }

  // ---------------------------------------------------------------- harbor view
  async function renderHarbor() {
    const host = $('#harbor');
    if (!window.Harbor) { host.replaceChildren(el('div', { class: 'empty', text: 'harbor.js did not load.' })); return; }
    if (!state.harbor) {
      state.harbor = window.Harbor.create(host, { onSelect: (o) => showDetail(o) });
      state.harbor.setBerths(state.berths);
    }
    const day = state.day;
    $('#harbor-day').value = day;
    let loads;
    try { loads = (await loadsForMonth(day.slice(0, 7))).filter((l) => l.day === day); }
    catch (err) { stopPlaying(); failed($('#harbor-panel'), err); return; }
    if (day !== state.day) return; // scrubbed past this day while it was loading
    const byBerth = {};
    const flags = { overCapacity: new Set(), unverifiable: new Set(), misfits: new Set(), unknownLength: new Set() };
    for (const l of loads) {
      byBerth[l.berth_id] = l.occupants.map(occupantOf);
      if (l.over_capacity) flags.overCapacity.add(l.berth_id);
      if (l.unverifiable) flags.unverifiable.add(l.berth_id);
      for (const o of l.occupants) {
        if (o.fit === 'misfit') flags.misfits.add(o.id);
        if (occupantOf(o).length_ft === null && o.kind === 'vessel') flags.unknownLength.add(o.id);
      }
    }
    state.harbor.setDay(day, byBerth, flags);
    renderHarborPanel(loads);
  }

  function renderHarborPanel(loads) {
    const berthById = new Map(state.berths.map((b) => [b.id, b]));
    const problems = [], lines = [];
    const lengthOf = (o) => (o.kind === 'vessel' ? fmtFt(occupantOf(o).length_ft) : 'whole berth');
    for (const l of loads) {
      const b = berthById.get(l.berth_id);
      if (!b) continue;
      const names = l.occupants.map((o) => `${o.name} (${lengthOf(o)})`).join(' + ');
      const shared = l.occupants.length > 1 && l.capacity_ft && l.used_ft !== null;
      if (l.occupants.length) lines.push(el('li', {}, el('strong', { text: b.name }), `: ${names}`, shared ? ` — ${fmtFt(l.used_ft)} of ${fmtFt(l.capacity_ft)} with clearance` : ''));
      if (l.over_capacity) {
        // the flag is the referee's; the arithmetic is only quoted when it is what the flag means
        const why = l.capacity_ft && l.known_ft > l.capacity_ft
          ? ` = ${l.unknown_count ? 'at least ' : ''}${fmtFt(l.known_ft)} > ${fmtFt(l.capacity_ft)}`
          : ' (an event, a closure or a one-occupant slip: the berth cannot be shared)';
        problems.push(el('li', { class: 'bad' }, `${b.name} over capacity: ${names}${why}`));
      } else if (l.unverifiable) {
        problems.push(el('li', { class: 'unknown' }, `${b.name} is shared and a length is missing, so it cannot be verified.`));
      }
      for (const o of l.occupants) {
        const len = occupantOf(o).length_ft;
        if (o.fit === 'misfit' && b.length_ft) problems.push(el('li', { class: 'bad' }, `${o.name} (${fmtFt(len)}) exceeds ${b.name} (${fmtFt(b.length_ft)}) by ${fmtFt(len - b.length_ft)}.`));
        if (o.fit === 'unknown') {
          problems.push(el('li', { class: 'unknown' }, len === null
            ? `${o.name}: length not on file, fit unknown.`
            : `${o.name}: fit cannot be checked because ${b.name} has no recorded length.`));
        }
      }
    }
    $('#harbor-panel').replaceChildren(
      el('h3', { text: state.day }),
      el('h4', { text: 'Findings' }), problems.length ? el('ul', {}, ...problems) : el('p', { class: 'ok', text: 'No conflicts today.' }),
      el('h4', { text: 'Occupancy' }), lines.length ? el('ul', {}, ...lines) : el('p', { class: 'empty', text: 'Empty harbor.' }));
  }

  function stepDay(n) {
    const next = addDays(state.day, n);
    if (Data.meta && Data.meta.last_day && next > addDays(Data.meta.last_day, 365)) { stopPlaying(); return; }
    state.day = next;
    renderHarbor();
  }
  function stopPlaying() {
    if (!state.timer) return;
    clearInterval(state.timer);
    state.timer = null;
    const b = $('#harbor-play'); b.textContent = '▶ Play'; b.setAttribute('aria-pressed', 'false');
    $('#harbor-panel').setAttribute('aria-live', 'polite');
  }
  function togglePlay() {
    if (state.timer) { stopPlaying(); return; }
    const b = $('#harbor-play'); b.textContent = '❚❚ Pause'; b.setAttribute('aria-pressed', 'true');
    $('#harbor-panel').setAttribute('aria-live', 'off'); // no announcement every 500 ms
    state.timer = setInterval(() => stepDay(1), 500);
  }

  // ---------------------------------------------------------------- audit view
  const stat = (n, label) => el('div', { class: 'stat' }, el('div', { class: 'n', text: String(n) }), el('div', { class: 'l', text: label }));
  const table = (headers, rows) => el('table', { class: 'data' }, el('thead', {}, el('tr', {}, ...headers.map((h) => el('th', { text: h })))),
    el('tbody', {}, ...rows.map((r) => el('tr', {}, ...r.map((c) => el('td', {}, c))))));

  // ---------------------------------------------------------------- vessel registries
  let registryTimer = null;
  let registrySeq = 0;
  async function renderRegistry() {
    const seq = ++registrySeq;
    const q = $('#registry-search').value.trim();
    const host = $('#registry');
    const count = $('#registry-count');
    host.setAttribute('aria-busy', 'true');
    host.replaceChildren(el('div', { class: 'empty', text: 'Loading vessels…' }));
    count.textContent = '';
    try {
      const vessels = await Data.vessels(q, 1000);
      if (seq !== registrySeq) return;
      count.textContent = vessels.length === 1000
        ? 'Showing the first 1,000 matches. Search by name to narrow the list.'
        : `${vessels.length} vessel${vessels.length === 1 ? '' : 's'}${q ? ' matching your search' : ''}`;
      const dimension = (n) => n == null ? el('span', { class: 'registry-unknown', text: 'Unknown' }) : fmtFt(n);
      host.replaceChildren(vessels.length
        ? table(['Vessel', 'Length overall', 'Draft', 'Operator', 'Notes'], vessels.map((v) => [
          v.name, dimension(v.length_ft), dimension(v.draft_ft), v.operator || '—',
          [v.rafts_ok ? 'Will raft alongside' : '', v.notes].filter(Boolean).join(' · ') || '—',
        ]))
        : el('div', { class: 'empty', text: q ? 'No vessels match this name. Try a shorter name or clear the search.' : 'No vessels are registered yet.' }));
    } catch (err) {
      if (seq !== registrySeq) return;
      failed(host, err);
    } finally {
      if (seq === registrySeq) host.setAttribute('aria-busy', 'false');
    }
  }

  async function renderAudit() {
    const host = $('#audit');
    host.replaceChildren(el('div', { class: 'empty', text: 'Loading…' }));
    let a;
    try { a = await Data.audit(); } catch (err) { failed(host, err); return; }
    const t = a.totals, c = a.audit_counts;
    host.replaceChildren(
      el('p', {}, 'The rules that guard the booking form, run over the whole imported history. ',
        el('a', { href: 'https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/AUDIT_REPORT.md', text: 'Full report' }), '.'),
      el('div', { class: 'stat-grid' },
        stat(`${a.years[0]}–${a.years[a.years.length - 1]}`, 'years covered'), stat(t.raw_stays, 'cell runs read from the grids'),
        stat(t.reservations, `reservations (${a.stitched} stitched across months)`), stat(t.annotations, 'notes kept as annotations, not bookings'),
        stat(`${a.vessel_stays_with_length} / ${a.vessel_stays}`, 'vessel stays with a known length'), stat(c.over_capacity_days, 'berth-days over capacity'),
        stat(c.misfits, 'vessels longer than their berth'), stat(c.unverifiable_days, 'shared days that cannot be verified'),
        stat(c.closure_conflicts, 'stays overlapping a closure'), stat(t.issues, 'issues logged instead of guessed')),
      el('p', { class: 'hint', text: 'Over capacity counts the feet arithmetic on shared faces. A stay that overlaps a closure is counted under closures; the grid and harbor paint those days red too.' }),
      el('h2', { text: 'Over-capacity runs' }),
      a.over_capacity.length ? table(['Berth', 'Days', 'Occupants', 'Used', 'Capacity'], a.over_capacity.map((r) => [r.berth, r.start === r.end ? r.start : `${r.start}..${r.end}`,
        r.occupants.map((o) => `${o.name} (${fmtFt(o.length_ft)})`).join(', '), fmtFt(r.used_ft), fmtFt(r.capacity_ft)])) : el('p', { class: 'empty', text: 'None: the legacy grid could not put two names in one cell, so within-row double bookings do not exist in it.' }),
      el('h2', { text: 'Vessels that do not fit their berth' }),
      a.misfits.length ? table(['Vessel', 'Berth', 'Dates', 'Finding'], a.misfits.map((m) => [m.reservation.name, m.berth, `${m.reservation.start}..${m.reservation.end}`, m.message])) : el('p', { class: 'empty', text: 'None among stays with a known length.' }),
      el('h2', { text: 'Stays overlapping a closure' }),
      a.closure_conflicts.length ? table(['Closure', 'Berth', 'Closure days', 'Displaced', 'Their days'], a.closure_conflicts.map((x) => [x.closure, x.berth, x.closure_days, x.displaced, x.displaced_days])) : el('p', { class: 'empty', text: 'None.' }),
      el('h2', { text: "The workbook's own summary vs. the grids (usage-days)" }),
      table(['Berth', ...a.summary_years.map(String)], a.summary_comparison.map((r) => [r.berth, ...r.summary.map((s, i) => `${s === null ? '–' : s} / ${r.ours[i]}`)])),
      el('p', { class: 'hint', text: 'sheet value / what the grids contain. The summary cannot be reproduced from the grids; it is reference material, not ground truth.' }),
      el('h2', { text: 'What the importer logged instead of guessing' }),
      table(['Issue', 'Count', 'Examples'], Object.entries(a.issues_by_kind).map(([k, n]) => [k, String(n), el('div', {}, ...(a.issue_examples[k] || []).map((e) => el('div', { class: 'hint', text: e })))])));
  }

  // ---------------------------------------------------------------- issues view
  async function renderIssues() {
    const kind = $('#issues-kind').value;
    const host = $('#issues');
    host.replaceChildren(el('div', { class: 'empty', text: 'Loading…' }));
    let data;
    try { data = await Data.issues(kind); } catch (err) { failed(host, err); return; }
    if (kind !== $('#issues-kind').value) return;
    const select = $('#issues-kind');
    if (select.options.length <= 1) {
      for (const [k, n] of Object.entries(data.counts)) select.append(el('option', { value: k, text: `${k} (${n})` }));
    }
    const total = kind ? (data.counts[kind] || 0) : Object.values(data.counts).reduce((a, b) => a + b, 0);
    const rows = data.issues.slice(0, 500);
    $('#issues-hint').textContent = `${total} issue(s)${total > rows.length ? `, first ${rows.length} shown` : ''}. Each one is something the importer noticed and did not silently fix.`;
    host.replaceChildren(el('div', { class: 'issues-wrap' }, table(['Sheet', 'Cell', 'Severity', 'Kind', 'What'], rows.map((i) => [i.sheet, i.cell, i.severity, i.kind, i.message]))));
  }

  // ---------------------------------------------------------------- detail dialog
  function showDetail(r) {
    const dialog = $('#detail');
    const berth = state.berths.find((b) => b.id === r.berth_id);
    const len = occupantOf(r).length_ft;
    const days = r.days || (Math.round((Date.parse(`${r.end}T00:00:00Z`) - Date.parse(`${r.start}T00:00:00Z`)) / 864e5) + 1);
    $('#detail-title').textContent = r.name || r.title;
    $('#detail-body').replaceChildren(el('dl', {},
      el('dt', { text: 'Kind' }), el('dd', { text: r.kind }),
      el('dt', { text: 'Berth' }), el('dd', { text: berth ? `${berth.name}${berth.length_ft ? ` (${fmtFt(berth.length_ft)})` : ''}` : String(r.berth_id) }),
      el('dt', { text: 'Length' }), el('dd', { text: r.kind === 'vessel' ? fmtFt(len) : 'whole berth' }),
      el('dt', { text: 'Dates' }), el('dd', { text: `${r.start} to ${r.end} (${days} days, inclusive)` }),
      el('dt', { text: 'Status' }), el('dd', { text: r.status || 'confirmed' }),
      r.override_reason ? el('dt', { text: 'Override' }) : null, r.override_reason ? el('dd', { text: r.override_reason }) : null,
      el('dt', { text: 'Source' }), el('dd', { text: r.legacy_ref ? `imported from ${r.legacy_ref}` : (r.source || 'manual') }),
      r.notes ? el('dt', { text: 'Notes' }) : null, r.notes ? el('dd', { text: r.notes }) : null));
    const cancel = $('#detail-cancel');
    cancel.hidden = !(Data.mode === 'api' && r.status !== 'cancelled' && r.id);
    cancel.onclick = async () => {
      if (!window.confirm(`Cancel ${r.name || r.title} (${r.start}..${r.end})? The record is kept, marked cancelled.`)) return;
      try { await Data.patchReservation(r.id, { status: 'cancelled' }); forgetLoads(); closeDetail(); showView(currentView()); }
      catch (err) { $('#detail-body').append(el('p', { class: 'verdict conflict', text: errorText(err) })); }
    };
    if (!dialog.open) dialog.showModal();
  }
  function closeDetail() { const dialog = $('#detail'); if (dialog.open) dialog.close(); }

  // ---------------------------------------------------------------- init
  function wireTabs() {
    const tabs = $$('.tabs button');
    tabs.forEach((b) => b.addEventListener('click', () => showView(b.dataset.view)));
    $('.tabs').addEventListener('keydown', (ev) => {
      const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const moves = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
      if (!(ev.key in moves)) return;
      ev.preventDefault();
      const next = tabs[(moves[ev.key] + tabs.length) % tabs.length];
      next.focus();
      showView(next.dataset.view);
    });
    window.addEventListener('hashchange', () => { const v = location.hash.slice(1); const next = VIEWS.includes(v) ? v : 'harbor'; if (next !== currentView()) showView(next); });
  }

  async function init() {
    const meta = await Data.init();
    const badge = $('#mode-badge');
    badge.textContent = Data.mode === 'api' ? 'Live · bookings saved' : `Read-only snapshot · ${meta.generated_on}`;
    badge.classList.toggle('static', Data.mode === 'static');
    $('#foot-note').textContent = `${meta.reservations || (meta.totals && meta.totals.reservations) || ''} reservations from ${meta.first_day || '?'} to ${meta.last_day || '?'}${Data.mode === 'static' ? `. ${meta.note}` : ''}`;
    state.berths = await Data.berths();
    const last = meta.last_day || '2019-12-31';
    state.month = last.slice(0, 7);
    state.day = last;

    $('#book-berth').replaceChildren(...state.berths.map((b) => el('option', { value: b.id, text: b.length_ft ? `${b.name} (${fmtFt(b.length_ft)}, ${b.capacity_mode})` : `${b.name} (${b.capacity_mode})` })));
    const now = new Date();
    const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    $('#book-start').value = Data.mode === 'api' ? today : last;
    $('#book-end').value = $('#book-start').value;
    $('#grid-today').onclick = () => { state.month = today.slice(0, 7); renderGrid(); };
    $('#grid-history').onclick = () => { state.month = '2017-07'; renderGrid(); };
    $('#harbor-today').onclick = () => { stopPlaying(); state.day = today; renderHarbor(); };
    $('#harbor-history').onclick = () => { stopPlaying(); state.day = '2017-07-12'; renderHarbor(); };
    $('#registry-search').oninput = () => {
      clearTimeout(registryTimer);
      ++registrySeq; // invalidate an in-flight result as soon as the search changes
      registryTimer = setTimeout(renderRegistry, 150);
    };
    wireTabs();
    $('#grid-prev').onclick = () => { const { y, m } = monthRange(state.month); state.month = m === 1 ? `${y - 1}-12` : `${y}-${pad(m - 1)}`; renderGrid(); };
    $('#grid-next').onclick = () => { const { y, m } = monthRange(state.month); state.month = m === 12 ? `${y + 1}-01` : `${y}-${pad(m + 1)}`; renderGrid(); };
    $('#grid-month').onchange = (e) => { if (isMonth(e.target.value)) { state.month = e.target.value; renderGrid(); } else e.target.value = state.month; };
    $('#book-kind').onchange = kindChanged;
    $('#book-vessel').oninput = vesselTyped;
    $('#book-vessel').onchange = vesselChosen;
    $('#vessel-length-save').onclick = saveVesselLength;
    $('#book-check').onclick = checkBooking;
    $('#book-suggest').onclick = suggestBerths;
    $('#book-form').onsubmit = saveBooking;
    $('#harbor-prev').onclick = () => { stopPlaying(); stepDay(-1); };
    $('#harbor-next').onclick = () => { stopPlaying(); stepDay(1); };
    $('#harbor-day').onchange = (e) => { if (e.target.value) { stopPlaying(); state.day = e.target.value; renderHarbor(); } };
    $('#harbor-play').onclick = togglePlay;
    $('#issues-kind').onchange = renderIssues;
    $('#detail-close').onclick = closeDetail;
    $('#detail').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeDetail(); }); // the backdrop
    if (Data.mode === 'static') {
      $$('.static-only').forEach((n) => { n.hidden = false; });
      ['#book-check', '#book-suggest', '#book-save', '#vessel-length-save'].forEach((s) => { $(s).disabled = true; });
    }
    kindChanged();
    showView(VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'harbor');
  }

  init().catch((err) => {
    $('#mode-badge').textContent = 'failed to load';
    $('main').replaceChildren(el('div', { class: 'empty', role: 'alert', text: `Could not load data: ${err.message}` }));
  });
})();
