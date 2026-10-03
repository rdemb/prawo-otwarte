'use strict';
// Session-only measurements: never accept descriptions, queries or server error text.
(function (root) {
  function summarize(rows) {
    const model = rows.filter(row => row.modelAttempt);
    const completed = model.filter(row => ['basal', 'basal_abstained'].includes(row.method));
    const times = completed.map(row => row.ms).sort((a, b) => a - b);
    const middle = Math.floor(times.length / 2);
    const rated = model.filter(row => row.method === 'basal' && typeof row.rating === 'boolean');
    const benchmark = completed.filter(row => row.sampleId);
    return {
      attempts: model.length, completed: completed.length,
      proposals: completed.filter(row => row.method === 'basal' && row.predicted !== 'unknown').length,
      abstentions: completed.filter(row => row.method === 'basal_abstained' || row.predicted === 'unknown').length,
      unavailable: model.length - completed.length,
      medianMs: times.length ? (times.length % 2 ? times[middle] : (times[middle - 1] + times[middle]) / 2) : null,
      p95Ms: times.length >= 20 ? times[Math.ceil(times.length * .95) - 1] : null,
      rated: rated.length, positive: rated.filter(row => row.rating).length,
      benchmarkCount: benchmark.length,
      benchmarkMatches: benchmark.filter(row => row.method === 'basal' && row.predicted === row.expected).length,
      benchmarkDistinct: new Set(benchmark.map(row => row.sampleId)).size
    };
  }
  function createSession(limit = 50) {
    let rows = [], serial = 0;
    return {
      add(input) {
        const row = {
          id: ++serial, at: new Date().toISOString(),
          ms: Math.max(0, Math.round(Number(input.ms) || 0)),
          modelAttempt: input.modelAttempt === true,
          method: ['basal', 'basal_abstained', 'user', 'unavailable', 'error'].includes(input.method) ? input.method : 'error',
          sampleId: input.sampleId || null, expected: input.expected || null,
          predicted: input.predicted || null, rating: null
        };
        rows.push(row); rows = rows.slice(-limit); return row.id;
      },
      rate(id, rating) { const row = rows.find(item => item.id === id); if (row?.method === 'basal') row.rating = typeof rating === 'boolean' ? rating : null; },
      rows() { return rows.map(row => ({...row})); },
      summary() { return summarize(rows); },
      clear() { rows = []; }
    };
  }
  const api = {summarize, createSession};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PrawoMetrics = api;
})(globalThis);
