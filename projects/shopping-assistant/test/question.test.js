import {test} from 'node:test';
import assert from 'node:assert/strict';
import {evaluate} from '../dist/engine.js';
import {interpret, rankEvidence, validateExcerpts} from '../dist/question.js';

test('catalog names and paraphrases fill the existing form', () => {
  assert.deepEqual(interpret('Shift Walker on my feet for eight hours?'),
    {productId: 'AB-123', activity: 'standing', hours: 8});
});

test('ambiguity, missing duration and invalid durations require clarification', () => {
  for (const question of ['AB-123 CD-456 standing 8 hours', 'AB-123 standing all shift',
    'AB-123 walking and standing 8 hours', 'AB-123 standing -8 hours',
    'AB-123 standing 17 hours', 'AB-1234 standing 8 hours']) {
    assert.throws(() => interpret(question));
  }
});

test('semantic ranking preserves all eligible evidence and falls back for bad vectors', () => {
  const {relevant} = evaluate('CD-456', 'standing', 8);
  assert.deepEqual(rankEvidence(relevant, [[1,0],[0,1],[1,0],[0.5,0.5]]).map(r => r.id),
    ['CD-R3', 'CD-R2', 'CD-R1']);
  assert.equal(rankEvidence(relevant, [[1,0]]), relevant);
});

test('generation requires both sides verbatim and rejects invented or excluded claims', () => {
  const result = evaluate('AB-123', 'standing', 8);
  const excerpts = result.relevant.map(({id, text}) => ({id, text}));
  assert.equal(validateExcerpts(result, excerpts), excerpts);
  assert.equal(validateExcerpts(result, excerpts.slice(0, 1)), null);
  assert.equal(validateExcerpts(result, [excerpts[0], excerpts[0]]), null);
  assert.equal(validateExcerpts(result, [excerpts[0], {...excerpts[1], text: 'Guaranteed comfort'}]), null);
  assert.equal(validateExcerpts(result, [excerpts[0], {id: 'AB-123-SPEC', text: 'Comfort'}]), null);
  assert.equal(validateExcerpts(evaluate('EF-789', 'standing', 8), excerpts), null);
});
