// puppeteer-smoke-test for PROD_URL /newswire/#trends
const puppeteer = require('puppeteer');

(async () => {
  const PROD_URL = process.env.PROD_URL || 'https://api.paranoidmodels.com';
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(30000);

    // 1. Health check
    const healthRes = await page.goto(`${PROD_URL}/health`);
    if (healthRes.status() !== 200) {
      throw new Error(`/health returned ${healthRes.status()}`);
    }
    console.log(`[ok] Health endpoint 200`);

    // 2. Newswire page
    await page.goto(`${PROD_URL}/newswire/#trends`, { waitUntil: 'networkidle2' });
    console.log(`[ok] Loaded newswire/#trends`);

    // 3. Extract first card's data
    const card = await page.$('.news-card, .card, article');
    if (!card) {
      throw new Error(`No news card found`);
    }
    const kicker = await card.$eval('.kicker', el => el.textContent.trim()).catch(() => 'N/A');
    const lede   = await card.$eval('.lede', el => el.textContent.trim()).catch(() => 'N/A');

    console.log(`First card kicker: ${kicker}`);
    console.log(`First card lede:   ${lede}`);

    if (kicker === 'N/A' || lede === 'N/A') {
      throw new Error(`Missing kicker or lede text`);
    }
    console.log(`[ok] Card fields present`);

  } catch (err) {
    console.error(`[fail] ${err.message}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
