const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createSession} = require('../prawo/static/metrics.js');

test('empty session has no invented latency, accuracy or ratings', () => {
  const s = createSession().summary();
  assert.equal(s.medianMs, null); assert.equal(s.p95Ms, null);
  assert.equal(s.attempts, 0); assert.equal(s.rated, 0); assert.equal(s.benchmarkCount, 0);
});
test('latency includes abstentions but excludes manual notes and failures', () => {
  const session = createSession();
  for (const [method, ms, modelAttempt] of [['basal', 1000, true], ['basal_abstained', 3000, true], ['unavailable', 10, true], ['error', 40000, true], ['user', 20, false]]) session.add({method, ms, modelAttempt});
  const s = session.summary();
  assert.equal(s.attempts, 4); assert.equal(s.completed, 2);
  assert.equal(s.unavailable, 2); assert.equal(s.abstentions, 1); assert.equal(s.medianMs, 2000);
});
test('benchmark denominator includes abstention and repeated cases, excludes outages', () => {
  const session = createSession();
  const common = {modelAttempt:true, sampleId:'work', expected:'work', ms:100};
  session.add({...common, method:'basal', predicted:'work'});
  session.add({...common, method:'basal', predicted:'civil'});
  session.add({...common, method:'basal_abstained', predicted:'unknown'});
  session.add({...common, method:'unavailable'});
  session.add({...common, method:'error'});
  const s = session.summary();
  assert.equal(s.benchmarkCount, 3); assert.equal(s.benchmarkMatches, 1); assert.equal(s.benchmarkDistinct, 1);
});
test('ratings replace previous choice and can be withdrawn', () => {
  const session = createSession();
  const id = session.add({method:'basal', modelAttempt:true, predicted:'work'});
  session.rate(id, true); session.rate(id, false);
  assert.equal(session.summary().rated, 1); assert.equal(session.summary().positive, 0);
  session.rate(id, null); assert.equal(session.summary().rated, 0);
  session.rate(session.add({method:'user'}), true); assert.equal(session.summary().rated, 0);
});
test('P95 is withheld until 20 completed model responses and uses nearest rank', () => {
  const session = createSession();
  for (let n = 1; n <= 19; n++) session.add({method:'basal', modelAttempt:true, ms:n * 1000});
  assert.equal(session.summary().p95Ms, null);
  session.add({method:'basal_abstained', modelAttempt:true, ms:20000});
  assert.equal(session.summary().p95Ms, 19000); assert.equal(session.summary().medianMs, 10500);
});
test('bounded session exports no description, query or error text; clear removes results', () => {
  const session = createSession(50);
  for (let n = 0; n < 55; n++) session.add({method:'error', ms:n, description:'PRIVATE_DESCRIPTION', query:'PRIVATE_QUERY', error:'PRIVATE_ERROR'});
  assert.equal(session.rows().length, 50); assert.equal(session.rows()[0].ms, 5);
  assert.ok(!JSON.stringify(session.rows()).includes('PRIVATE_'));
  const copy = session.rows(); copy[0].method = 'basal'; assert.equal(session.rows()[0].method, 'error');
  session.clear(); assert.equal(session.rows().length, 0); assert.equal(session.summary().medianMs, null);
});
