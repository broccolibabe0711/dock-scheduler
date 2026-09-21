const { test } = require('node:test');
const assert = require('node:assert/strict');
const { filterRows, counts, isDate, validFilters } = require('../site/audit.js');
const defaults = { query: '', berth: '', from: '', to: '', type: '' };
const rows = [
  { category: 'fit', severity: 'conflict', berth_id: 2, names: ['R/V Clear Tern'], start: '2010-07-29', end: '2010-08-03' },
  { category: 'closure', severity: 'conflict', berth_id: 6, names: ['Utility work', 'OSV Amber Reef'], start: '2017-07-11', end: '2017-07-15' },
  { category: 'unknown_fit', severity: 'unknown', berth_id: 6, names: ['OSV Amber Reef'], start: '2017-07-09', end: '2017-07-18' },
  { category: 'unverifiable', severity: 'unknown', berth_id: 6, names: ['OSV Amber Reef', 'M/V Other'], start: '2017-07-12', end: '2017-07-12' },
];
const { matching, insertTemplate, hasPrompts, dateChoices, lengthChoices } = require('../site/inputs.js');

test('suggestion searches match slash variants and never alter their source', () => {
  const source = [{ value: 'OSV Amber Reef', label: 'OSV Amber Reef · length unknown' },
    { value: 'R/V Clear Tern', label: 'R/V Clear Tern · 120 ft' }];
  const before = JSON.stringify(source);
  assert.deepEqual(matching(source, ' OS/V AMBER '), [source[0]]);
  assert.deepEqual(matching(source, 'no such vessel'), []);
  assert.equal(JSON.stringify(source), before);
});
test('note templates preserve existing text and flag unfinished prompts', () => {
  assert.equal(insertTemplate('Existing note.', 'Arrival: [time].'), 'Existing note. Arrival: [time].');
  assert.equal(insertTemplate('Existing note.', 'Arrival: [time].', true), 'Existing note.\nArrival: [time].');
  assert.equal(hasPrompts('Arrival: [time].'), true);
  assert.equal(hasPrompts('Arrival: 09:00.'), false);
});
test('date shortcuts count inclusive stays across leap days and years', () => {
  const leap = dateChoices({ today: '2028-02-27', start: '2028-02-27' });
  assert.equal(leap.find((c) => c.label.startsWith('7-day')).value, '2028-03-04');
  const year = dateChoices({ start: '2026-12-31' });
  assert.equal(year.find((c) => c.label.startsWith('30-day')).value, '2027-01-29');
  assert.equal(dateChoices({ optional: true })[0].value, '');
  assert.ok(dateChoices({ today: '2026-09-20', month: true }).every((c) => /^\d{4}-\d{2}$/.test(c.value)));
});
test('measurement suggestions contain only the selected vessel’s recorded value or unknown', () => {
  assert.deepEqual(lengthChoices(null).map((c) => c.value), ['']);
  assert.deepEqual(lengthChoices({ length_ft: null }).map((c) => c.value), ['']);
  assert.deepEqual(lengthChoices({ length_ft: 120 }).map((c) => c.value), ['', '120']);
});

test('combined name, berth, date and type filters include the final occupied day', () => {
  assert.deepEqual(filterRows(rows, { query: ' OS/V AMBER ', berth: '6', from: '2017-07-15', to: '2017-07-15', type: 'conflict' }), [rows[1]]);
  assert.deepEqual(filterRows(rows, { ...defaults, query: 'Clear Tern', from: '2010-08-03', to: '2010-08-03' }), [rows[0]]);
});
test('date filters retain stays crossing month boundaries but exclude the following day', () => {
  assert.deepEqual(filterRows(rows, { ...defaults, from: '2010-08-01', to: '2010-08-02' }), [rows[0]]);
  assert.deepEqual(filterRows(rows, { ...defaults, from: '2010-08-04', to: '2010-08-04' }), []);
});
test('closure title is searchable and unknowns stay separate from definite conflicts', () => {
  assert.deepEqual(filterRows(rows, { ...defaults, query: 'utility work' }), [rows[1]]);
  assert.deepEqual(filterRows(rows, { ...defaults, type: 'unknown' }), [rows[2], rows[3]]);
  assert.deepEqual(filterRows(rows, { ...defaults, type: 'unverifiable' }), [rows[3]]);
});
test('clear filters restores all evidence and counts describe the matching subset', () => {
  assert.deepEqual(filterRows(rows, defaults), rows);
  assert.deepEqual(counts(filterRows(rows, { ...defaults, type: 'conflict' })), { total: 2, conflicts: 2, unknown: 0, berths: 2 });
  assert.deepEqual(counts([]), { total: 0, conflicts: 0, unknown: 0, berths: 0 });
});
test('saved filters reject malformed dates, reversed ranges and unknown finding categories', () => {
  assert.equal(validFilters({ ...defaults, from: '2017-02-29' }), false);
  assert.equal(validFilters({ ...defaults, from: '2017-07-15', to: '2017-07-11' }), false);
  assert.equal(validFilters({ ...defaults, type: 'fictional' }), false);
  assert.equal(validFilters(null), false);
  assert.equal(validFilters({ ...defaults, query: null }), false);
  assert.equal(validFilters(defaults), true);
  assert.equal(isDate('2028-02-29'), true);
  assert.equal(isDate('2026-04-31'), false);
});
test('filtering and summarizing cannot mutate the historical evidence', () => {
  const original = JSON.stringify(rows);
  counts(filterRows(rows, { ...defaults, query: 'Amber' }));
  assert.equal(JSON.stringify(rows), original);
});
