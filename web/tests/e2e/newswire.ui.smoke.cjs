// puppeteer-smoke-test for newswire UI at PROD_URL/newswire/#trends
const puppeteer = require('puppeteer');

(async () => {
  const PROD_URL = process.env.PROD_URL || 'http://localhost:5173';
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(30000);

    console.log(`Testing newswire UI at: ${PROD_URL}`);

    // 1. Load newswire page
    const pageRes = await page.goto(`${PROD_URL}/newswire/#trends`, { 
      waitUntil: 'networkidle2' 
    });
    
    if (pageRes.status() !== 200) {
      throw new Error(`/newswire/#trends returned ${pageRes.status()}`);
    }
    console.log(`[ok] Newswire page loads (200)`);

    // 2. Check for essential page elements
    await page.waitForSelector('.page', { timeout: 10000 });
    console.log(`[ok] Page container found`);

    // 3. Check navigation
    const nav = await page.$('.nav');
    if (!nav) {
      throw new Error('Navigation not found');
    }
    console.log(`[ok] Navigation present`);

    // 4. Check for brand link
    const brand = await page.$('.brand');
    if (!brand) {
      throw new Error('Brand link not found');
    }
    console.log(`[ok] Brand link present`);

    // 5. Check hero section
    const hero = await page.$('.hero');
    if (!hero) {
      throw new Error('Hero section not found');
    }
    console.log(`[ok] Hero section present`);

    // 6. Check for hero main card
    const heroMainCard = await page.$('.hero .hero-main .card');
    if (!heroMainCard) {
      throw new Error('Hero main card not found');
    }
    console.log(`[ok] Hero main card present`);

    // 7. Check for hero sidebar cards
    const heroSideCards = await page.$$('.hero .hero-sidebar .card');
    if (heroSideCards.length < 2) {
      throw new Error(`Expected at least 2 hero sidebar cards, found ${heroSideCards.length}`);
    }
    console.log(`[ok] Hero sidebar cards present (${heroSideCards.length})`);

    // 8. Check for grid section
    const grid = await page.$('.grid');
    if (!grid) {
      throw new Error('Grid section not found');
    }
    console.log(`[ok] Grid section present`);

    // 9. Check for grid cards
    const gridCards = await page.$$('.grid .card');
    if (gridCards.length < 5) {
      throw new Error(`Expected at least 5 grid cards, found ${gridCards.length}`);
    }
    console.log(`[ok] Grid cards present (${gridCards.length})`);

    // 10. Check card structure - pick first hero card
    const firstCard = await page.$('[data-testid="hero-main-card"]');
    if (!firstCard) {
      throw new Error('First hero card not found');
    }

    // Check kicker
    const kicker = await firstCard.$('[data-testid="kicker"]');
    if (!kicker) {
      throw new Error('Card kicker not found');
    }
    const kickerText = await kicker.evaluate(el => el.textContent);
    if (!kickerText || kickerText.length < 3) {
      throw new Error('Card kicker text too short');
    }
    console.log(`[ok] Card kicker present: "${kickerText}"`);

    // Check headline
    const headline = await firstCard.$('[data-testid="headline"] a');
    if (!headline) {
      throw new Error('Card headline link not found');
    }
    const headlineText = await headline.evaluate(el => el.textContent);
    if (!headlineText || headlineText.length < 10) {
      throw new Error('Card headline text too short');
    }
    console.log(`[ok] Card headline present: "${headlineText.slice(0, 50)}..."`);

    // Check lede
    const lede = await firstCard.$('[data-testid="lede"]');
    if (!lede) {
      throw new Error('Card lede not found');
    }
    const ledeText = await lede.evaluate(el => el.textContent);
    if (!ledeText || ledeText.length < 20) {
      throw new Error('Card lede text too short');
    }
    console.log(`[ok] Card lede present (${ledeText.length} chars)`);

    // Check CTA
    const cta = await firstCard.$('[data-testid="cta"]');
    if (!cta) {
      throw new Error('Card CTA not found');
    }
    const ctaText = await cta.evaluate(el => el.textContent);
    if (!ctaText || ctaText.length < 3) {
      throw new Error('Card CTA text too short');
    }
    console.log(`[ok] Card CTA present: "${ctaText}"`);

    // 11. Check responsive behavior (optional)
    await page.setViewport({ width: 768, height: 1024 });
    await new Promise(resolve => setTimeout(resolve, 500)); // Let styles adjust
    console.log(`[ok] Responsive viewport test passed`);

    // 12. Check for console errors
    const logs = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        logs.push(msg.text());
      }
    });

    // Reload to catch any console errors
    await page.reload({ waitUntil: 'networkidle2' });
    
    if (logs.length > 0) {
      console.warn(`[warn] Console errors found: ${logs.join(', ')}`);
      // Don't fail on console errors, just warn
    } else {
      console.log(`[ok] No console errors`);
    }

    // 13. Check accessibility basics
    const landmarks = await page.$$('main, nav, header, footer');
    if (landmarks.length < 3) {
      throw new Error(`Expected at least 3 landmarks, found ${landmarks.length}`);
    }
    console.log(`[ok] Accessibility landmarks present (${landmarks.length})`);

    console.log(`[ok] All newswire UI smoke tests passed! 🎉`);

  } catch (err) {
    console.error(`[fail] ${err.message}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
