/* Duotone card image pipeline (CommonJS)
 * Usage: node scripts/images/duotone.js
 * IN:  process.env.NEWS_IMG_SRC (default: assets/news-images)
 * OUT: artifacts/newswire/img/card/<name>-{480,768,1200}.webp
 */
const fs = require('fs');
const path = require('path');
let sharp;
try { sharp = require('sharp'); } catch (e) {
  console.warn('[images] sharp not installed or incompatible. Skipping duotone.');
  process.exit(0);
}

const IN = process.env.NEWS_IMG_SRC || 'assets/news-images';
const OUT = 'artifacts/newswire/img/card';
const SIZES = [480, 768, 1200];
const DUO = { fg: '#D1D5DB', bg: '#0B0F1A' };

fs.mkdirSync(OUT, { recursive: true });
if (!fs.existsSync(IN)) {
  console.warn(`(images) Source folder not found: ${IN}. Create it or set NEWS_IMG_SRC.`);
  process.exit(0);
}

const files = fs.readdirSync(IN).filter(f => /\.(jpe?g|png|webp)$/i.test(f));
if (!files.length) {
  console.warn(`(images) No source images in ${IN}. Skipping.`);
  process.exit(0);
}

(async () => {
  for (const f of files) {
    const src = path.join(IN, f);
    const base = path.parse(f).name;

    for (const w of SIZES) {
      const g = sharp(src).resize({ width: w, height: Math.round(w * 9 / 16), fit: 'cover' }).grayscale();
      const gray = await g.toBuffer();

      const bgTile = await sharp({
        create: { width: 16, height: 16, channels: 3, background: DUO.bg }
      }).png().toBuffer();

      const outBuf = await sharp(gray)
        .recomb([[0.95, 0, 0], [0, 0.95, 0], [0, 0, 0.95]])
        .modulate({ brightness: 1.0, saturation: 1.0 })
        .composite([{ input: bgTile, tile: true, blend: 'multiply' }])
        .toColorspace('srgb')
        .webp({ quality: 82, effort: 4 })
        .toBuffer();

      const out = path.join(OUT, `${base}-${w}.webp`);
      fs.writeFileSync(out, outBuf);
    }
  }
  console.log(`✓ Duotone generated → ${OUT}/<name>-{480,768,1200}.webp`);
})().catch(err => {
  console.error('[images] Duotone failed:', err.message);
  process.exit(1);
});
