export const REQUIRED_HEADERS = [
  'id', 'time', 'customer', 'merchant', 'category', 'amount', 'country',
  'home_country', 'device', 'velocity_1h', 'usual_amount', 'chargebacks_30d',
  'status', 'source_dispute_outcome', 'source_dispute_reasons',
  'source_chargeback_count',
];

const formatAmount = value => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
  }
  if (quoted) throw new Error('CSV has an unterminated quoted field.');
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

export function parseTransactionsCsv(text) {
  const rows = parseCsvRows(text);
  if (rows.length < 2) throw new Error('CSV must include a header and at least one transaction.');
  const [headers, ...body] = rows;
  const missing = REQUIRED_HEADERS.filter(header => !headers.includes(header));
  if (missing.length) throw new Error(`CSV is missing required columns: ${missing.join(', ')}`);
  const seenIds = new Set();

  return body.map((cells, index) => {
    if (cells.length !== headers.length) throw new Error(`CSV row ${index + 2} has ${cells.length} fields; expected ${headers.length}.`);
    const raw = Object.fromEntries(headers.map((header, column) => [header, cells[column]]));
    if (!raw.id.trim() || !raw.customer.trim() || !raw.merchant.trim()) {
      throw new Error(`CSV row ${index + 2} is missing an ID, account, or merchant.`);
    }
    if (seenIds.has(raw.id)) throw new Error(`Duplicate transaction ID: ${raw.id}`);
    seenIds.add(raw.id);

    const numeric = {};
    for (const key of ['amount', 'velocity_1h', 'usual_amount', 'chargebacks_30d', 'source_chargeback_count']) {
      numeric[key] = Number(raw[key]);
      if (!Number.isFinite(numeric[key])) throw new Error(`CSV row ${index + 2} has an invalid ${key}.`);
    }
    if (numeric.amount < 0 || numeric.usual_amount < 0 || numeric.velocity_1h < 1
      || numeric.chargebacks_30d < 0 || numeric.source_chargeback_count < 0) {
      throw new Error(`CSV row ${index + 2} has a negative amount or invalid count.`);
    }
    if (!['Completed', 'Declined'].includes(raw.status)) {
      throw new Error(`CSV row ${index + 2} has an unsupported authorization status.`);
    }
    if (Number.isNaN(Date.parse(raw.time))) throw new Error(`CSV row ${index + 2} has an invalid timestamp.`);

    return {
      ...raw,
      ...numeric,
      source_dispute_reasons: raw.source_dispute_reasons ? raw.source_dispute_reasons.split(';') : [],
    };
  });
}

export async function loadDemoData(fetcher = fetch) {
  const [transactionsResponse, policiesResponse] = await Promise.all([
    fetcher('./data/transactions.csv'),
    fetcher('./data/policies.json'),
  ]);
  if (!transactionsResponse.ok || !policiesResponse.ok) {
    throw new Error('Demo data files could not be loaded.');
  }
  const [csv, policies] = await Promise.all([
    transactionsResponse.text(),
    policiesResponse.json(),
  ]);
  const transactions = parseTransactionsCsv(csv);
  if (!Array.isArray(policies) || policies.some(policy => !policy.id || !Array.isArray(policy.tags) || !policy.text)) {
    throw new Error('Policy file has an invalid schema.');
  }
  return { transactions, policies };
}

export function scoreTransaction(tx, policies) {
  const signals = [];
  let score = 0;
  const ratio = tx.usual_amount > 0 ? tx.amount / tx.usual_amount : 0;

  if (ratio >= 5) {
    score += 28;
    signals.push({ label: 'Amount far above observed pattern', detail: `${formatAmount(tx.amount)} vs. prior median ${formatAmount(tx.usual_amount)} source units (${ratio.toFixed(1)}×)`, weight: 'High' });
  } else if (ratio >= 2.5) {
    score += 16;
    signals.push({ label: 'Amount above observed pattern', detail: `${formatAmount(tx.amount)} vs. prior median ${formatAmount(tx.usual_amount)} source units (${ratio.toFixed(1)}×)`, weight: 'Medium' });
  }
  if (tx.velocity_1h >= 6) {
    score += 24;
    signals.push({ label: 'High authorization velocity', detail: `${tx.velocity_1h} transactions in the last hour`, weight: 'High' });
  } else if (tx.velocity_1h >= 4) {
    score += 13;
    signals.push({ label: 'Elevated authorization velocity', detail: `${tx.velocity_1h} transactions in the last hour`, weight: 'Medium' });
  }
  if (tx.device === 'Shared device') {
    score += 20;
    signals.push({ label: 'Device shared across accounts', detail: 'The source data associates this device fingerprint with multiple accounts', weight: 'High' });
  }
  const crossBorder = tx.home_country !== 'Unknown' && tx.country !== 'Unknown' && tx.country !== tx.home_country;
  if (crossBorder) {
    score += 16;
    signals.push({ label: 'Cross-border activity', detail: `Account country ${tx.home_country}; merchant country ${tx.country}`, weight: 'Medium' });
  }
  if (tx.chargebacks_30d > 0) {
    score += 8;
    signals.push({ label: 'Recent dispute history', detail: `${tx.chargebacks_30d} dispute(s) recorded in 30 days; context only`, weight: 'Low' });
  }

  score = Math.min(score, 99);
  const level = score >= 60 ? 'High' : score >= 35 ? 'Medium' : 'Low';
  const tags = new Set();
  if (ratio >= 2.5) tags.add('amount');
  if (tx.velocity_1h >= 4) tags.add('velocity');
  if (tx.device === 'Shared device') tags.add('device');
  if (crossBorder) tags.add('cross-border');
  if (tx.chargebacks_30d > 0) {
    tags.add('chargeback');
    tags.add('repeat-dispute');
  }
  const evidence = policies.filter(policy => policy.tags.some(tag => tags.has(tag)));
  let recommendation = level === 'High' ? 'Escalate for human review'
    : level === 'Medium' ? 'Verify customer context' : 'Continue standard monitoring';
  if (tx.chargebacks_30d > 0) recommendation += '; treat dispute history as context, not proof';

  return {
    transaction: tx,
    score,
    level,
    signals,
    evidence,
    recommendation,
    summary: `${level.toLowerCase()} risk score (${score}/100) based on ${signals.length} explainable signal(s). The score is a demonstration heuristic, not a validated production model.`,
  };
}

export function renderTransactionRow(result) {
  const tx = result.transaction;
  const level = result.level.toLowerCase();
  const status = tx.status.toLowerCase();
  return `<tr data-id="${escapeHtml(tx.id)}"><td><div class="tx-id">${escapeHtml(tx.id)}</div><div class="tx-time">${new Date(tx.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false })} UTC</div></td><td><div class="merchant">${escapeHtml(tx.merchant)}</div><div class="customer">${escapeHtml(tx.customer)} · ${escapeHtml(tx.category)}</div></td><td class="amount">${formatAmount(tx.amount)}</td><td class="channel">${escapeHtml(tx.country)} · ${escapeHtml(tx.device === 'Shared device' ? 'Shared device' : 'Unique device')}</td><td class="risk-cell"><div class="risk-head ${level}"><span>${result.score}</span><span>/ 100</span></div><div class="risk-track"><div class="risk-fill ${level}" style="width:${result.score}%"></div></div></td><td><span class="badge ${status === 'declined' ? 'review' : 'cleared'}">${escapeHtml(tx.status)}</span></td><td class="row-arrow">›</td></tr>`;
}