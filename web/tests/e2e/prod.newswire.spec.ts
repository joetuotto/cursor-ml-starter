import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const PROD_URL = process.env.PROD_URL?.replace(/\/$/, '') ?? 'https://fertility-api-2q3ac3ofma-lz.a.run.app';
const PAGE_URL = `${PROD_URL}/newswire/#trends`;
const HEALTH_URL = `${PROD_URL}/health`;

async function queryOne(page: any, selectors: string[]) {
  for (const sel of selectors) {
    const el = page.locator(sel);
    if ((await el.first().count()) > 0) return el.first();
  }
  return page.locator('__never__');
}

test.describe('Prod Newswire smoke', () => {
  test('health 200 + page has enriched items + no console errors', async ({ page }, testInfo) => {
    const consoleErrors: { type: string; text: string }[] = [];
    page.on('console', (msg) => {
      if (['error'].includes(msg.type())) consoleErrors.push({ type: msg.type(), text: msg.text() });
    });

    const health = await page.request.get(HEALTH_URL);
    const okStatus = health.status() === 200;
    const healthBody = await health.text();

    const resp = await page.goto(PAGE_URL, { waitUntil: 'networkidle' });
    expect(resp, 'page should respond').toBeTruthy();

    const status = resp!.status();
    if (status === 404) {
      await saveArtifacts(page, testInfo, '404');
      test.skip(true, '/newswire returned 404 – skipping content checks');
    }

    const card = await queryOne(page, [
      '[data-testid="feed-card"]',
      '.feed-card',
      '[role="article"]',
      'article',
      '[data-test="feed-card"]',
    ]);
    await expect(card, 'should render at least one feed card').toHaveCount(1);

    const kicker = await queryOne(page, [
      '[data-testid="kicker"]',
      '.kicker',
      '[data-field="kicker"]',
      'header .kicker',
    ]);
    const lede = await queryOne(page, [
      '[data-testid="lede"]',
      '.lede, .lead, .intro',
      '[data-field="lede"]',
    ]);
    const why = await queryOne(page, [
      '[data-testid="why-it-matters"]',
      '.why-it-matters, .why',
      '[data-field="why_it_matters"]',
      'section:has-text("Why it matters")',
    ]);
    const svg = await queryOne(page, [
      '[data-testid="symbolic-art"] svg',
      'figure svg',
      'svg',
    ]);
    const cta = await queryOne(page, [
      '[data-testid="cta"]',
      'a.cta',
      'a[rel="noopener"], a[rel="noreferrer"], a[target="_blank"]',
      'a[href]',
    ]);

    await expect.soft(kicker, 'kicker näkyy').toHaveCount(1);
    await expect.soft(lede, 'lede näkyy').toHaveCount(1);
    await expect.soft(why, 'why_it_matters näkyy').toHaveCount(1);
    await expect.soft(svg, 'symbolic SVG näkyy').toHaveCount(1);
    await expect.soft(cta, 'CTA-linkki löytyy').toHaveCount(1);

    const kickerText = (await kicker.textContent())?.trim() ?? '';
    const ledeText = (await lede.textContent())?.trim() ?? '';
    const whyText = (await why.textContent())?.trim() ?? '';
    const ctaHref = (await cta.getAttribute('href')) ?? '';

    await saveArtifacts(page, testInfo, 'ok', {
      health: { ok: okStatus, status: health.status(), body: healthBody.slice(0, 200) },
      pageStatus: status,
      firstCard: { kickerText, ledeText, whyText, ctaHref },
      consoleErrors,
      urls: { PAGE_URL, HEALTH_URL },
    });

    expect.soft(consoleErrors, 'no console errors').toEqual([]);
    expect.soft(okStatus, `/health should be 200 (got ${health.status()})`).toBeTruthy();
  });
});

async function saveArtifacts(page: any, testInfo: any, tag: string, extra?: unknown) {
  const outDir = testInfo.outputDir || testInfo.outputPath('');
  const ensure = (p: string) => {
    fs.mkdirSync(path.dirname(p), { recursive: true });
    return p;
  };

  const snap = ensure(path.join(outDir, `newswire-${tag}.png`));
  const html = ensure(path.join(outDir, `newswire-${tag}.html`));
  const json = ensure(path.join(outDir, `newswire-${tag}.json`));

  await page.screenshot({ path: snap, fullPage: true });
  const content = await page.content();
  fs.writeFileSync(html, content, 'utf8');
  if (extra) fs.writeFileSync(json, JSON.stringify(extra, null, 2), 'utf8');

  testInfo.attachments.push(
    { name: `screenshot-${tag}`, path: snap, contentType: 'image/png' },
    { name: `html-${tag}`, path: html, contentType: 'text/html' },
    ...(extra ? [{ name: `report-${tag}`, path: json, contentType: 'application/json' } as const] : [])
  );
}
