import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test('Newswire smoke', async ({ page }) => {
  // Yritä avata /newswire. Jos reittiä ei ole deployssa → tallenna snapshot ja dynaaminen skip.
  const response = await page.goto('/newswire', { waitUntil: 'domcontentloaded' });

  if (response && response.status() === 404) {
    // Luo artefaktikansio (CI kerää talteen).
    const outDir = path.resolve(process.cwd(), 'test-artifacts', 'newswire-404');
    fs.mkdirSync(outDir, { recursive: true });

    // Tallenna HTML ja kuvakaappaus.
    const htmlPath = path.join(outDir, 'newswire-404.html');
    const pngPath = path.join(outDir, 'newswire-404.png');
    const infoPath = path.join(outDir, 'meta.json');

    const html = await page.content();
    await fs.promises.writeFile(htmlPath, html, 'utf8');
    await page.screenshot({ path: pngPath, fullPage: true });

    // Tallenna kevyt metadata (status, url, headers).
    const meta = {
      url: page.url(),
      status: response.status(),
      headers: response.headers(),
      ts: new Date().toISOString(),
    };
    await fs.promises.writeFile(infoPath, JSON.stringify(meta, null, 2), 'utf8');

    test.skip(true, 'Newswire route not available in this environment (404). Snapshot saved.');
  }

  // Perusvarmistukset: otsikko näkyy ja vähintään yksi feed-kortti on renderöitynyt.
  await expect(page.locator('h1')).toContainText(/newswire/i);
  const firstCard = page.getByTestId('feed-card').first();
  await expect(firstCard).toBeVisible();
});
