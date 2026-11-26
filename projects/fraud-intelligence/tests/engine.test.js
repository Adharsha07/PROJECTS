import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  loadDemoData,
  parseTransactionsCsv,
  renderTransactionRow,
  scoreTransaction,
} from '../engine.js';

const csv = await readFile(new URL('../data/transactions.csv', import.meta.url), 'utf8');
const policyText = await readFile(new URL('../data/policies.json', import.meta.url), 'utf8');
const policies = JSON.parse(policyText);
const sample = {
  id: 'TX-TEST-1',
  time: '2026-04-01T12:00:00.000Z',
  customer: 'ACCT-001',
  merchant: 'Test Shop',
  category: 'Retail',
  amount: 600,
  country: 'GB',
  home_country: 'US',
  device: 'Shared device',
  velocity_1h: 6,
  usual_amount: 100,
  chargebacks_30d: 1,
  status: 'Completed',
  source_dispute_outcome: 'Fraud-coded dispute recorded',
  source_dispute_reasons: ['fraud_card_not_present'],
  source_chargeback_count: 1,
};

test('parses and validates the full source CSV sample', () => {
  const transactions = parseTransactionsCsv(csv);
  assert.equal(transactions.length, 2165);
  assert.equal(transactions.reduce((sum, tx) => sum + tx.source_chargeback_count, 0), 76);
  assert.equal(transactions[0].source_dispute_reasons instanceof Array, true);
  assert.ok(transactions.every(tx => Number.isFinite(tx.amount)));
  assert.doesNotMatch(csv.split('\n', 1)[0], /email|ip_block/i);
});

test('rejects missing columns, malformed rows, duplicate IDs and bad numeric values', () => {
  assert.throws(() => parseTransactionsCsv('id,amount\nTX-1,12\n'), /missing required columns/);
  const header = csv.split('\n', 1)[0];
  assert.throws(() => parseTransactionsCsv(`${header}\n"unterminated`), /unterminated quoted field/);
  const validRow = csv.split('\n')[1];
  assert.throws(() => parseTransactionsCsv(`${header}\n${validRow}\n${validRow}`), /Duplicate transaction ID/);
  const badAmount = validRow.replace(/,[^,]+$/, ',not-a-number');
  assert.throws(() => parseTransactionsCsv(`${header}\n${badAmount}`), /invalid source_chargeback_count|invalid amount/);
});

test('scores each configured signal and explains why the sample is high risk', () => {
  const result = scoreTransaction(sample, policies);
  assert.equal(result.score, 96);
  assert.equal(result.level, 'High');
  assert.deepEqual(result.signals.map(signal => signal.label), [
    'Amount far above observed pattern',
    'High authorization velocity',
    'Device shared across accounts',
    'Cross-border activity',
    'Recent dispute history',
  ]);
  assert.equal(result.recommendation.startsWith('Escalate for human review'), true);
  assert.ok(result.summary.includes('not a validated production model'));
});

test('retrieves only policies whose tags match a transaction signal', () => {
  const result = scoreTransaction(sample, policies);
  assert.deepEqual(result.evidence.map(policy => policy.id), ['POL-07', 'POL-12', 'POL-18']);
  const ordinary = scoreTransaction({
    ...sample,
    amount: 20,
    usual_amount: 100,
    velocity_1h: 1,
    device: 'Known device',
    country: 'US',
    home_country: 'US',
    chargebacks_30d: 0,
  }, policies);
  assert.deepEqual(ordinary.evidence, []);
});

test('post-transaction dispute outcomes do not change scores or signal explanations', () => {
  const original = scoreTransaction(sample, policies);
  const changedOutcome = scoreTransaction({
    ...sample,
    source_dispute_outcome: 'No chargeback recorded',
    source_dispute_reasons: [],
    source_chargeback_count: 0,
  }, policies);
  assert.equal(changedOutcome.score, original.score);
  assert.deepEqual(changedOutcome.signals, original.signals);
  assert.deepEqual(changedOutcome.evidence, original.evidence);
});

test('loads the CSV and policies through the same fetch boundary used by the app', async () => {
  const calls = [];
  const fakeFetch = async path => {
    calls.push(path);
    if (path.endsWith('.csv')) return { ok: true, text: async () => csv };
    return { ok: true, json: async () => policies };
  };
  const loaded = await loadDemoData(fakeFetch);
  assert.deepEqual(calls, ['./data/transactions.csv', './data/policies.json']);
  assert.equal(loaded.transactions.length, 2165);
  assert.equal(loaded.policies.length, 3);
  const rows = loaded.transactions.slice(0, 100).map(tx => renderTransactionRow(scoreTransaction(tx, loaded.policies))).join('');
  assert.equal((rows.match(/<tr\b/g) || []).length, 100);
  assert.match(rows, /TX-/);
});

test('escapes transaction text before producing table markup', () => {
  const result = scoreTransaction({ ...sample, merchant: '<script>alert(1)</script>' }, policies);
  const row = renderTransactionRow(result);
  assert.doesNotMatch(row, /<script>/);
  assert.match(row, /&lt;script&gt;/);
});