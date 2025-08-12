import { test, expect } from '@playwright/test';

const PROD_URL = process.env.PROD_URL || 'http://localhost:5173';

test.describe('Finnish Newswire Feed', () => {
  test('should load Finnish newswire page', async ({ page }) => {
    await page.goto(`${PROD_URL}/newswire/fi`);
    
    // Check page loads
    await expect(page).toHaveTitle(/PARANOID Models/);
    
    // Check Finnish-specific elements
    await expect(page.locator('h1')).toContainText('🇫🇮');
    await expect(page.locator('h1')).toContainText('Suomi');
    
    // Check navigation
    await expect(page.locator('.nav-link.active')).toContainText('Suomi');
    
    // Wait for content to load (or error state)
    await page.waitForSelector('.loading-state, .error-state, .news-card-wrapper, .empty-state', { timeout: 10000 });
    
    // If content loaded, check Finnish-specific features
    const hasContent = await page.locator('.news-card-wrapper').count() > 0;
    
    if (hasContent) {
      // Check FI badges on cards
      await expect(page.locator('.fi-badge').first()).toContainText('FI');
      
      // Check for Finnish perspective sections
      const hasFinnishPerspective = await page.locator('.finnish-perspective').count() > 0;
      if (hasFinnishPerspective) {
        await expect(page.locator('.fi-label').first()).toContainText('🇫🇮 Suomen näkökulma');
      }
    }
  });

  test('should navigate between Global and Finnish feeds', async ({ page }) => {
    // Start on Finnish page
    await page.goto(`${PROD_URL}/newswire/fi`);
    await expect(page.locator('.nav-link.active')).toContainText('Suomi');
    
    // Navigate to Global
    await page.click('text=Global');
    await expect(page).toHaveURL(/\/newswire/);
    await expect(page.locator('h1')).not.toContainText('🇫🇮');
    
    // Navigate back to Finnish
    await page.goto(`${PROD_URL}/newswire/fi`);
    await expect(page.locator('.nav-link.active')).toContainText('Suomi');
  });

  test('API endpoint should return Finnish data', async ({ request }) => {
    const response = await request.get(`${PROD_URL}/newswire/fi`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('origin_country_filter', 'FI');
    
    if (data.items.length > 0) {
      const item = data.items[0];
      expect(item).toHaveProperty('origin_country', 'FI');
      expect(item).toHaveProperty('source_name');
      expect(item).toHaveProperty('kicker');
      expect(item).toHaveProperty('lede');
      
      // Check for Finnish-specific fields
      expect(item).toHaveProperty('local_fi');
      expect(item).toHaveProperty('local_fi_score');
      expect(typeof item.local_fi_score).toBe('number');
      expect(item.local_fi_score).toBeGreaterThanOrEqual(0);
      expect(item.local_fi_score).toBeLessThanOrEqual(1);
    }
  });

  test('should handle empty state gracefully', async ({ page }) => {
    // Mock empty response
    await page.route('**/newswire/fi', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          origin_country_filter: 'FI'
        })
      });
    });
    
    await page.goto(`${PROD_URL}/newswire/fi`);
    await expect(page.locator('.empty-state')).toBeVisible();
    await expect(page.locator('.empty-state')).toContainText('Ei uutisia saatavilla');
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Mock error response
    await page.route('**/newswire/fi', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });
    
    await page.goto(`${PROD_URL}/newswire/fi`);
    await expect(page.locator('.error-state')).toBeVisible();
    await expect(page.locator('.error-state')).toContainText('Virhe uutisten latauksessa');
    
    // Check retry button
    await expect(page.locator('.retry-button')).toBeVisible();
  });

  test('should display Finnish content correctly', async ({ page }) => {
    // Mock Finnish content
    await page.route('**/newswire/fi', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{
            id: 'test-fi-1',
            title: 'Suomen Pankki nostaa korkoja',
            kicker: 'Rahapolitiikka kiristyy',
            lede: 'Keskuspankki nosti ohjauskorkoa 0,25 prosenttiyksiköllä.',
            why_it_matters: 'Vaikuttaa asuntolainoihin ja kulutukseen',
            cta: { label: 'Lue lisää', url: '#' },
            published_at: '2025-08-11T10:00:00Z',
            source_name: 'YLE',
            origin_country: 'FI',
            local_fi: 'Korkokorotus vaikuttaa erityisesti asuntomarkkinoihin.',
            local_fi_score: 0.95
          }],
          total: 1,
          origin_country_filter: 'FI'
        })
      });
    });
    
    await page.goto(`${PROD_URL}/newswire/fi`);
    
    // Check content displays
    await expect(page.locator('.kicker')).toContainText('Rahapolitiikka kiristyy');
    await expect(page.locator('.headline')).toContainText('Suomen Pankki nostaa korkoja');
    
    // Check Finnish perspective
    await expect(page.locator('.finnish-perspective')).toBeVisible();
    await expect(page.locator('.fi-label')).toContainText('🇫🇮 Suomen näkökulma');
    await expect(page.locator('.fi-score')).toContainText('95%');
    await expect(page.locator('.fi-content')).toContainText('asuntomarkkinoihin');
  });
});
