/* Filter the Python audit's evidence; never rejudge a booking in the browser. */
(() => {
  'use strict';
  const LABELS = {
    fit: 'Vessel too long', capacity: 'Over capacity', closure: 'Closure overlap',
    unknown_fit: 'Fit unknown', unverifiable: 'Shared capacity unknown',
    inactive: 'Berth out of service', orphaned: 'Missing berth',
  };
  const STORAGE_KEY = 'dock.audit.filters.v1';
  const DEFAULTS = { query: '', berth: '', from: '', to: '', type: '' };
  const fold = (text) => text.toLowerCase().replace(/\//g, '').replace(/\s+/g, ' ').trim();
  function isDate(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`))
      && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
  }
  function validFilters(value) {
    if (!value || typeof value !== 'object') return false;
    return Object.keys(DEFAULTS).every((key) => typeof value[key] === 'string')
      && value.query.length <= 120 && (!value.from || isDate(value.from)) && (!value.to || isDate(value.to))
      && !(value.from && value.to && value.from > value.to)
      && ['', 'conflict', 'unknown', ...Object.keys(LABELS)].includes(value.type);
  }
  function filterRows(rows, filters) {
    const q = fold(filters.query);
    return rows.filter((r) => (!filters.berth || String(r.berth_id) === filters.berth)
      && (!filters.from || r.end >= filters.from) && (!filters.to || r.start <= filters.to)
      && (!filters.type || r.category === filters.type || r.severity === filters.type)
      && (!q || fold(r.names.join(' ')).includes(q)));
  }
  function counts(rows) {
    return { total: rows.length, conflicts: rows.filter((r) => r.severity === 'conflict').length,
      unknown: rows.filter((r) => r.severity === 'unknown').length,
      berths: new Set(rows.map((r) => r.berth_id)).size };
  }

  function create(host, data, { el, stat, onExplore }) {
    if (!Array.isArray(data.findings)) throw new Error('The historical finding details are missing. Reload to get the latest audit.');
    const rows = data.findings;
    let page = 0, filters = { ...DEFAULTS }, remembered = false, preferenceMessage = '';
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (!validFilters(parsed)) throw new Error('invalid filters');
        filters = Object.fromEntries(Object.keys(DEFAULTS).map((k) => [k, parsed[k]]));
        remembered = true;
      }
    } catch (_) { preferenceMessage = 'Saved filters could not be loaded. You can still filter this audit.'; }
    const berths = [...new Map(rows.map((r) => [String(r.berth_id), r.berth])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
    if (filters.berth && !berths.some(([id]) => id === filters.berth)) filters.berth = '';
    const field = (text, node) => el('label', {}, text, node);
    const query = el('input', { type: 'search', id: 'audit-query', placeholder: 'Vessel or event name…', maxlength: '120', value: filters.query });
    const berth = el('select', { id: 'audit-berth' }, el('option', { value: '', text: 'All berths with findings' }),
      ...berths.map(([id, name]) => el('option', { value: id, text: name })));
    const type = el('select', { id: 'audit-type' }, ...[
      ['', 'All findings'], ['conflict', 'Confirmed conflicts'], ['unknown', 'Missing evidence'], ...Object.entries(LABELS),
    ].map(([value, text]) => el('option', { value, text })));
    berth.value = filters.berth;
    type.value = filters.type;
    const from = el('input', { type: 'date', id: 'audit-from', value: filters.from });
    const to = el('input', { type: 'date', id: 'audit-to', value: filters.to });
    const remember = el('input', { type: 'checkbox', id: 'audit-remember' });
    remember.checked = remembered;
    const preferenceStatus = el('p', { class: 'hint', role: 'status', text: preferenceMessage });
    const status = el('p', { class: 'hint', role: 'status', id: 'audit-results-status' });
    const summary = el('div', { class: 'stat-grid audit-stats' });
    const list = el('ul', { class: 'audit-findings', 'aria-label': 'Matching historical findings' });
    const prev = el('button', { type: 'button', text: 'Previous 25' });
    const next = el('button', { type: 'button', text: 'Next 25' });
    const pageLabel = el('span', { class: 'hint' });
    const error = el('p', { role: 'alert', class: 'audit-error' });
    const clear = el('button', { type: 'button', text: 'Clear filters' });
    const quick = el('div', { class: 'audit-quick', role: 'group', 'aria-label': 'Finding shortcuts' },
      ...[['', 'All findings'], ['conflict', 'Confirmed conflicts'], ['unknown', 'Missing evidence']].map(([value, text]) =>
        el('button', { type: 'button', text, onclick: () => { type.value = value; changed(); } })));
    const form = el('form', { class: 'audit-filters', 'aria-label': 'Filter the historical audit' },
      el('div', { class: 'audit-fields' }, field('Vessel or event', query), field('Berth', berth), field('Finding type', type),
        field('From (inclusive)', from), field('To (inclusive)', to)),
      el('div', { class: 'audit-filter-actions' }, quick, clear,
        el('label', { class: 'check-label' }, remember, 'Remember my filters on this browser')),
      el('p', { class: 'hint', text: 'Filters combine. Dates include overlapping stays; closure dates show the actual overlap. Remembering is optional and local to this browser.' }),
      error, preferenceStatus);
    form.onsubmit = (ev) => { ev.preventDefault(); changed(); };
    host.replaceChildren(form, summary, status,
      el('p', { class: 'hint', text: 'Fit findings count stays; shared-capacity findings count berth-days. One stay can have more than one finding.' }), list,
      el('div', { class: 'audit-pagination', role: 'group', 'aria-label': 'Finding pages' }, prev, pageLabel, next));

    function savePreferences() {
      try {
        if (remember.checked) localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
        else localStorage.removeItem(STORAGE_KEY);
        preferenceStatus.textContent = remember.checked ? 'Filters remembered on this browser.' : '';
      } catch (_) { preferenceStatus.textContent = 'This browser cannot save preferences. Your current filters still work.'; }
    }
    function render() {
      const matches = filterRows(rows, filters), tally = counts(matches);
      page = Math.max(0, Math.min(page, Math.ceil(matches.length / 25) - 1));
      const first = page * 25, shown = matches.slice(first, first + 25);
      summary.replaceChildren(stat(tally.total, 'matching findings'), stat(tally.conflicts, 'confirmed conflicts'),
        stat(tally.unknown, 'missing-evidence findings'), stat(tally.berths, 'berths with matching findings'));
      const range = filters.from || filters.to ? `${filters.from || 'start of history'} through ${filters.to || 'end of history'}` : 'all dates';
      const selectedBerth = berth.options[berth.selectedIndex].text;
      status.textContent = `${matches.length} of ${rows.length} historical findings · ${selectedBerth} · ${range}${filters.query ? ` · names containing “${filters.query}”` : ''} · ${type.options[type.selectedIndex].text}.`;
      for (const b of quick.children) b.setAttribute('aria-pressed', String(
        b.textContent === ({ '': 'All findings', conflict: 'Confirmed conflicts', unknown: 'Missing evidence' }[filters.type])));
      list.replaceChildren(...shown.map((r) => el('li', { class: `audit-finding ${r.severity}` },
        el('div', { class: 'audit-finding-top' }, el('span', { class: `finding-badge ${r.severity}`, text: LABELS[r.category] || r.category }),
          el('span', { class: 'hint', text: r.start === r.end ? r.start : `${r.start} → ${r.end}` })),
        el('h3', { text: r.names.join(' + ') }), el('p', { class: 'finding-berth', text: r.berth }),
        el('p', { text: r.message }),
        r.sources.length ? el('details', {}, el('summary', { text: 'Workbook source' }), ...r.sources.map((s) => el('p', { class: 'provenance', text: s }))) : null,
        el('button', { type: 'button', text: 'Open these dates in Grid + Harbor', onclick: () => onExplore(r, filters) }))));
      if (!matches.length) list.append(el('li', { class: 'empty', text: 'No findings match these filters. Try a wider date range, another finding type, or Clear filters. This does not prove the schedule was safe where measurements are missing.' }));
      prev.disabled = page === 0;
      next.disabled = first + 25 >= matches.length;
      pageLabel.textContent = matches.length ? `${first + 1}–${first + shown.length} of ${matches.length}` : '0 findings';
    }
    function changed() {
      const proposed = { query: query.value.trim(), berth: berth.value, from: from.value, to: to.value, type: type.value };
      if (!form.checkValidity() || !validFilters(proposed)) {
        error.textContent = 'Enter valid dates, with From on or before To. Results below still use the last valid filters.';
        return;
      }
      error.textContent = '';
      filters = proposed;
      page = 0;
      savePreferences();
      render();
    }
    query.oninput = changed;
    for (const node of [berth, type, from, to]) node.onchange = changed;
    remember.onchange = savePreferences;
    clear.onclick = () => { query.value = berth.value = type.value = from.value = to.value = ''; changed(); };
    prev.onclick = () => { page--; render(); };
    next.onclick = () => { page++; render(); };
    render();
  }
  const api = { create, filterRows, counts, isDate, validFilters };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else window.Audit = api;
})();
