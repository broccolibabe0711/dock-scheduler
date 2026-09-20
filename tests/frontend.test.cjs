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
