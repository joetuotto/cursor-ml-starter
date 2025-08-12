// Auto-remediator for feeds: fixes categories, image base, drops low-quality cards.
// Usage: node scripts/remediate/feeds.js
const fs = require('fs');
const path = require('path');

const FEEDS_DIR = 'artifacts/feeds';
const FILES = ['trends.en.json', 'trends.fi.json'];
const DEFAULT_CAT = 'geopolitics';
const IMG_BASE = 'https://paranoidmodels.com/newswire/img/card/';

function isLimp(text) {
  if (!text) return true;
  const bad = /(it remains to be seen|experts say|analysts say|time will tell)/i;
  return bad.test(text);
}

function ensureImageBase(card) {
  let img = card.image || '';
  // If it ends with a file extension, replace with slug base
  const hasExt = /\.(jpe?g|png|webp)$/i.test(img);
  if (!img || hasExt) {
    const slugSrc = (card.kicker || card.headline || 'card').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');
    const slug = slugSrc.slice(0, 28) || 'card';
    card.image = IMG_BASE + slug;
  }
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
    if (!card._meta.category) { card._meta.category = DEFAULT_CAT; changed++; }
    ensureImageBase(card);
    const limp = isLimp(card.lede) || isLimp(card.why_it_matters);
    if (okHersh(card) && !limp) out.push(card);
    else dropped++;
  }
  fs.writeFileSync(fp, JSON.stringify(out, null, 2));
  console.log(`[remediate] ${f}: kept ${out.length}/${src.length} (dropped ${src.length - out.length})`);
}
console.log(`[remediate] changed fields: ${changed}, dropped total: ${dropped}`);



