import {products} from './engine.js';

export function interpret(question) {
  const input = question.toLowerCase();
  const tokens = input.match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) ?? [];
  const matches = products.filter(({id, name}) => tokens.includes(id.toLowerCase()) ||
    (' ' + input.replace(/[^a-z0-9]+/g, ' ') + ' ').includes(' ' + name.toLowerCase() + ' '));
  const activities = Object.entries({
    standing: /\b(stand(?:ing)?|on my feet)\b/,
    desk: /\b(desk|sitting|seated)\b/,
    walking: /\b(walk(?:ing)?)\b/
  }).filter(([, pattern]) => pattern.test(input));
  const words = 'one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen'.split(' ');
  const durations = [...input.matchAll(/(?<![\w.-])(-?\d+(?:\.\d+)?|[a-z]+)[ -]+hours?\b/g)]
    .map(([, value]) => /^-?\d/.test(value) ? Number(value) : words.indexOf(value) + 1);
  if (matches.length !== 1) throw new Error('Specify one catalog product by name or ID.');
  if (activities.length !== 1) throw new Error('Choose one activity: standing, desk use, or walking.');
  if (durations.length !== 1 || durations[0] < 1 || durations[0] > 16) {
    throw new Error('Specify one duration between 1 and 16 hours.');
  }
  return {productId: matches[0].id, activity: activities[0][0], hours: durations[0]};
}

export function rankEvidence(reviews, vectors) {
  const [query, ...documents] = vectors;
  const valid = vector => Array.isArray(vector) && vector.length === query?.length &&
    vector.length > 0 && vector.every(Number.isFinite) && Math.hypot(...vector) > 0;
  if (documents.length !== reviews.length || !vectors.every(valid)) return reviews;
  const score = vector => vector.reduce((sum, value, i) => sum + value * query[i], 0) /
    (Math.hypot(...query) * Math.hypot(...vector));
  return reviews.map((review, i) => ({review, score: score(documents[i])}))
    .sort((a, b) => b.score - a.score).map(({review}) => review);
}

// Generation selects and orders verbatim excerpts. Code owns all conclusions.
export function validateExcerpts(result, excerpts) {
  if (!Array.isArray(excerpts) || excerpts.length !== result.relevant.length) return null;
  const unseen = new Map(result.relevant.map(review => [review.id, review]));
  for (const excerpt of excerpts) {
    const review = unseen.get(excerpt?.id);
    if (!review || excerpt.text !== review.text) return null;
    unseen.delete(review.id);
  }
  return excerpts;
}
