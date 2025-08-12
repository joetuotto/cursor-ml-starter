#!/usr/bin/env node
/**
 * News feed validator for Paranoid models (CommonJS)
 * Usage:
 *  node scripts/validate/news_feed_check.js artifacts/feeds/trends.en.json artifacts/feeds/trends.fi.json
 */
const fs = require('fs');
const path = require('path');

const DEFAULT_FEEDS = [
  'artifacts/feeds/trends.en.json',
  'artifacts/feeds/trends.fi.json',
];

const ALLOWED_CATEGORIES = new Set([
  'geopolitics', 'infoops', 'espionage', 'highpol', 'secrethist', 'elite', 'general'
]);
const ALLOWED_LANG = new Set(['en','fi']);

const BANNED_PHRASES = [
  'why it matters:',
  'this could be significant',
  'experts say',
  'raises questions',
  'time will tell',
  'could have implications',
  'ongoing situation',
  'as of press time',
  'controversial move',
  'it remains to be seen',
  'generally speaking',
];

const MIN_LEN = {
  kicker: 3,
  headline: 12,
  lede: 40,
  why_it_matters: 40,
};

const feeds = process.argv.slice(2);
const feedFiles = feeds.length ? feeds : DEFAULT_FEEDS.filter(f => fs.existsSync(f));
if (!feedFiles.length) {
  console.error('No feed files provided and defaults not found. Aborting.');
  process.exit(2);
}

const results = [];
let errorCount = 0;

async function headOk(url) {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    return res.ok;
  } catch {
    return false;
  }
}

function hasBannedPhrases(text) {
  const t = String(text || '').toLowerCase();
  return BANNED_PHRASES.find(p => t.includes(p));
}

function uniq(arr) {
  return Array.from(new Set((arr || []).filter(Boolean)));
}

async function validateCard(card, idx, langHint) {
  const issues = [];
  const warn = [];

  // Mandatory fields
  for (const key of ['kicker', 'headline', 'lede', 'why_it_matters']) {
    const val = card?.[key];
    if (!val || typeof val !== 'string' || val.trim().length < MIN_LEN[key]) {
      issues.push(`missing_or_short:${key}`);
    }
    const banned = hasBannedPhrases(val);
    if (banned) issues.push(`banned_phrase_in_${key}:"${banned}"`);
  }

  // Hersh/dark-tolerance must-haves
  const analysisText = `${card?.analysis || ''} ${card?._meta?.analysis || ''}`.toLowerCase();
  const hasRisk = Boolean(card?.risk_scenario || card?._meta?.risk_scenario || card?.risk || card?._meta?.risk);
  if (!hasRisk) issues.push('missing:risk_scenario');
  const whoSyn = /(who benefits|beneficiaries|cui bono|kuka hyötyy|hyötyjät)/i.test(analysisText);
  const hasWho = Boolean(card?.who_benefits || card?._meta?.who_benefits || whoSyn);
  if (!hasWho) issues.push('missing:who_benefits');

  // Category (accept _meta.category or category)
  const category = card?._meta?.category || card?.category;
  if (!category) issues.push('missing:_meta.category');
  else if (!ALLOWED_CATEGORIES.has(String(category))) issues.push(`invalid_category:${category}`);

  // Language must be explicit and match feed
  const lang = card?.lang;
  if (!lang) issues.push('missing:lang');
  else if (!ALLOWED_LANG.has(String(lang))) issues.push(`invalid_lang:${lang}`);
  else if (lang !== langHint) warn.push(`lang_mismatch_feed:${lang}!=${langHint}`);

  // Refs (accept refs or sources fallback)
  let refs = card?.refs || card?._meta?.refs;
  if (!Array.isArray(refs) || !refs.length) {
    const srcs = Array.isArray(card?.sources) ? card.sources : [];
    refs = srcs.map(s => (typeof s === 'string' ? s : s?.url)).filter(Boolean);
  }
  const uniqRefs = uniq(refs);
  if (!uniqRefs.length) issues.push('missing:refs');
  const urlish = uniqRefs.some(r => /^https?:\/\//i.test(r));
  if (!urlish) warn.push('refs_without_url_like_entries');

  // Image checks: accept base string or image object
  let imgBase = card?._meta?.image_base || card?.image || card?._meta?.image;
  if (imgBase && typeof imgBase === 'object') {
    imgBase = imgBase.card || imgBase.hero || imgBase.thumb || '';
  }
  if (!imgBase) {
    warn.push('missing:image_base');
  } else {
    const isFixed = /\.(webp|jpe?g|png)$/i.test(imgBase);
    const base = isFixed ? imgBase.replace(/(-\d+)?\.(webp|jpe?g|png)$/i, '') : imgBase;
    const candidates = isFixed ? [imgBase] : [
      `${base}-480.webp`, `${base}-768.webp`, `${base}-1200.webp`
    ];
    let allOk = true;
    for (const url of candidates) {
      /* eslint-disable no-await-in-loop */
      const ok = await headOk(url);
      if (!ok) {
        allOk = false;
        warn.push(`image_head_fail:${url}`);
      }
    }
    if (!allOk) warn.push('image_srcset_incomplete_or_unreachable');
  }

  return { idx, lang: langHint, issues, warn };
}

(async function run() {
  for (const f of feedFiles) {
    const raw = fs.readFileSync(f, 'utf8');
    let items = [];
    try {
      items = JSON.parse(raw);
      if (!Array.isArray(items)) throw new Error('feed is not array');
    } catch (e) {
      results.push({ feed: f, fatal: `JSON parse error: ${e.message}` });
      errorCount++;
      continue;
    }
    const langHint = /(\.fi\.json)$/i.test(f) ? 'fi' : 'en';

    for (let i = 0; i < items.length; i++) {
      const r = await validateCard(items[i], i, langHint);
      results.push({ feed: f, ...r });
      if (r.issues.length) errorCount += r.issues.length;
    }
  }

  // Pretty print summary
  const byFeed = new Map();
  for (const r of results) {
    const key = r.feed || r.fatal || 'unknown';
    if (!byFeed.has(key)) byFeed.set(key, []);
    byFeed.get(key).push(r);
  }
  console.log('── Validation Report ─────────────────────────────────────────');
  for (const [feed, rows] of byFeed.entries()) {
    const fatals = rows.filter(x => x.fatal);
    if (fatals.length) {
      console.log(`✖ ${feed}`);
      fatals.forEach(x => console.log('   •', x.fatal));
      continue;
    }
    const total = rows.filter(x => x.idx !== undefined).length;
    const withIssues = rows.filter(x => (x.issues || []).length);
    const withWarns = rows.filter(x => (x.warn || []).length);
    console.log(`• ${feed}  (cards=${total}, issues=${withIssues.length}, warns=${withWarns.length})`);
    for (const r of rows) {
      if (!r.idx && !r.issues && !r.warn) continue;
      if ((r.issues || []).length || (r.warn || []).length) {
        console.log(`  - [${r.lang}] card#${r.idx}:`);
        if (r.issues?.length) console.log('     issues:', r.issues.join(', '));
        if (r.warn?.length) console.log('     warns :', r.warn.join(', '));
      }
    }
  }
  console.log('──────────────────────────────────────────────────────────────');

  if (errorCount > 0) {
    console.error(`✖ Validation failed with ${errorCount} issue(s).`);
    process.exit(1);
  } else {
    console.log('✓ Validation passed (no blocking issues).');
  }
})().catch(e => {
  console.error('Validator crashed:', e);
  process.exit(3);
});
