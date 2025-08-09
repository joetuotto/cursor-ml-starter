import { test, expect } from '@playwright/test';

test('Newswire smoke', async ({ page }) => {
  // Yritä avata /newswire. Jos reittiä ei ole deployssa → dynaaminen skip.
  const response = await page.goto('/newswire', { waitUntil: 'domcontentloaded' });

  if (response && response.status() === 404) {
    test.skip(true, 'Newswire route not available in this environment.');
  }

  // Perusvarmistukset: otsikko näkyy ja vähintään yksi feed-kortti on renderöitynyt.
  await expect(page.locator('h1')).toContainText(/newswire/i);
  const firstCard = page.getByTestId('feed-card').first();
  await expect(firstCard).toBeVisible();
});
