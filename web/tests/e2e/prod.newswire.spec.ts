// web/tests/e2e/prod.newswire.spec.ts
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const PROD_URL = process.env.PROD_URL ?? 'https://fertility-api-2q3ac3ofma-lz.a.run.app';
const NEWSWIRE = `${PROD_URL.replace(/\/$/, '')}/newswire/#trends`;
const ARTIFACT_JSON = process.env.ENRICHED_JSON ?? path.resolve('artifacts/report.enriched.json');

function mdTrim(s?: string | null) {
  return (s ?? '').replace(/\s+/g, ' ').trim();
}

test.setTimeout(30_000);

test.describe('Prod newswire smoke', () => {
  test('health is 200', async ({ request }) => {
    const res = await request.get(`${PROD_URL}/health`, { timeout: 10_000 });
    expect(res.status(), 'GET /health must be HTTP 200').toBe(200);
  });

  test('trends page renders and cards look right', async ({ page }, testInfo) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    const resp = await page.goto(NEWSWIRE, { waitUntil: 'domcontentloaded' });
    expect(resp?.status(), 'GET /newswire/#trends must be HTTP 200').toBe(200);

    // Best-effort korttiselector – säädä tarvittaessa:
    const cardSel = '[data-testid="news-card"], article.news-card, .news-card';
    await page.waitForSelector(cardSel, { timeout: 10_000 });

    const cards = await page.$$(cardSel);
    expect(cards.length, 'At least 1 card should render').toBeGreaterThan(0);

    // Tarkistetaan ensimmäiset 3 korttia (tai vähemmän jos ei riitä)
    const count = Math.min(cards.length, 3);
    for (let i = 0; i < count; i++) {
      const card = cards[i];

      // Yleisimmät kenttäselektorit (data-testid -> class -> semanttinen tagi)
      const kicker = await card.locator('[data-testid="kicker"], .kicker, header .kicker, [class*="kicker"]').first().textContent().catch(() => '');
      const lede = await card.locator('[data-testid="lede"], .lede, p.lede, [class*="lede"]').first().textContent().catch(() => '');
      const why = await card.locator('[data-testid="why-it-matters"], .why-it-matters, [class*="whyItMatters"]').first().textContent().catch(() => '');
      const ctaBtn = await card.locator('[data-testid="cta"], a.cta, button.cta, [class*="cta"]').first();
      const svg = await card.locator('svg').first();

      expect(mdTrim(kicker), `card #${i + 1}: kicker missing`).not.toHaveLength(0);
      expect(mdTrim(lede), `card #${i + 1}: lede missing`).not.toHaveLength(0);
      expect(mdTrim(why), `card #${i + 1}: why_it_matters missing`).not.toHaveLength(0);
      await expect(ctaBtn, `card #${i + 1}: CTA missing`).toBeVisible();
      await expect(svg, `card #${i + 1}: symbolic SVG missing`).toBeVisible();
    }

    // Pehmeä vertailu enriched-artifacttiin (jos löytyy)
    if (fs.existsSync(ARTIFACT_JSON)) {
      try {
        const raw = fs.readFileSync(ARTIFACT_JSON, 'utf-8');
        const data = JSON.parse(raw);
        const firstCard = cards[0];
        const pageKicker = mdTrim(await firstCard.locator('[data-testid="kicker"], .kicker, header .kicker, [class*="kicker"]').first().textContent().catch(() => ''));
        const pageLede = mdTrim(await firstCard.locator('[data-testid="lede"], .lede, p.lede, [class*="lede"]').first().textContent().catch(() => ''));

        const dataKicker = mdTrim(data?.kicker ?? data?.items?.[0]?.kicker);
        const dataLede = mdTrim(data?.lede ?? data?.items?.[0]?.lede);

        // Ei kaadeta, mutta ilmoitetaan selkeästi mismatch
        if (dataKicker) {
          expect(pageKicker, 'first card kicker should match enriched JSON (normalized)').toContain(dataKicker.slice(0, Math.min(32, dataKicker.length)));
        }
        if (dataLede) {
          expect(pageLede, 'first card lede should roughly match enriched JSON (normalized)').toContain(dataLede.slice(0, Math.min(48, dataLede.length)));
        }
      } catch (e) {
        testInfo.attach('enriched-compare-note', { body: `Compare skipped or soft-failed: ${(e as Error).message}` });
      }
    } else {
      testInfo.attach('enriched-compare-note', { body: `Artifact not found at ${ARTIFACT_JSON}; skipped compare.` });
    }

    // Talletetaan screenshot ja HTML
    const shot = await page.screenshot({ fullPage: true });
    await testInfo.attach('screenshot', { body: shot, contentType: 'image/png' });
    const html = await page.content();
    await testInfo.attach('html', { body: html, contentType: 'text/html' });

    // Failaa jos on konsolivirheitä
    expect(consoleErrors, `Console errors:\n${consoleErrors.join('\n')}`).toHaveLength(0);
  });
});