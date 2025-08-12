// Auto-remediator for feeds: fixes categories, image base, drops low-quality cards.
// Usage: node scripts/remediate/feeds.js
const fs = require('fs');
const path = require('path');

const FEEDS_DIR = 'artifacts/feeds';
const FILES = ['trends.en.json', 'trends.fi.json'];
const DEFAULT_CAT = 'geopolitics';
const IMG_BASE = 'https://paranoidmodels.com/newswire/img/card/';
const ALLOWED_CATEGORIES = new Set(['geopolitics','infoops','espionage','highpol','secrethist','elite']);

function isLimp(text) {
  if (!text) return true;
  const bad = /(it remains to be seen|experts say|analysts say|time will tell)/i;
  return bad.test(text);
}

function ensureImageBase(card) {
  const current = card._meta?.image_base || card.image || '';
  const endsWithSuffix = /(-\d+)?\.(jpe?g|png|webp)$/i.test(current);
  const needsGen = !current || endsWithSuffix;
  const slugSrc = (card.kicker || card.headline || 'card')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  const slug = (slugSrc || 'card').slice(0, 28);
  const base = needsGen ? (IMG_BASE + slug) : current.replace(/(-\d+)?\.(jpe?g|png|webp)$/i, '');

  card._meta = card._meta || {};
  card._meta.image_base = base;
  // Keep legacy field for compatibility
  card.image = base;
}

function okHersh(card) {
  const wm = (card.why_it_matters || '').toLowerCase();
  const hasWhoBenefits = wm.includes('who benefits');
  const hasRisk = /risk|scenario|contingency/.test(wm);
  const refsOk = Array.isArray(card.refs) && card.refs.length > 0;
  return hasWhoBenefits && hasRisk && refsOk;
}

let changed = 0, dropped = 0;

for (const f of FILES) {
  const fp = path.join(FEEDS_DIR, f);
  if (!fs.existsSync(fp)) { console.warn(`[remediate] missing: ${fp}`); continue; }
  const src = JSON.parse(fs.readFileSync(fp, 'utf8'));
  const out = [];
  for (const card of src) {
    card._meta = card._meta || {};
    // Ensure language per file
    const lang = /\.fi\.json$/i.test(f) ? 'fi' : 'en';
    if (card.lang !== lang) { card.lang = lang; changed++; }

    // Category remediation with allowlist fallback
    let cat = card._meta.category || card.category || DEFAULT_CAT;
    if (!ALLOWED_CATEGORIES.has(String(cat))) {
      cat = DEFAULT_CAT;
      changed++;
    }
    card._meta.category = cat;

    ensureImageBase(card);
    const limp = isLimp(card.lede) || isLimp(card.why_it_matters);
    if (okHersh(card) && !limp) out.push(card);
    else dropped++;
  }
  fs.writeFileSync(fp, JSON.stringify(out, null, 2));
  console.log(`[remediate] ${f}: kept ${out.length}/${src.length} (dropped ${src.length - out.length})`);
}
console.log(`[remediate] changed fields: ${changed}, dropped total: ${dropped}`);



