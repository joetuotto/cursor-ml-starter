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

    // 2. Schema endpoint
    const schemaRes = await page.goto(`${PROD_URL}/schemas/feed_item.json`);
    if (schemaRes.status() !== 200) {
      throw new Error(`/schemas/feed_item.json returned ${schemaRes.status()}`);
    }
    console.log(`[ok] Schema endpoint 200`);

    // 3. Predict endpoint test via fetch
    const predictRes = await page.evaluate(async (prodUrl) => {
      const response = await fetch(`${prodUrl}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emf: 1.5, income: 2500, urbanization: 0.6 })
      });
      return {
        status: response.status,
        data: await response.json()
      };
    }, PROD_URL);

    if (predictRes.status !== 200) {
      throw new Error(`/predict returned ${predictRes.status}`);
    }
    
    console.log(`[ok] Predict endpoint 200`);
    console.log(`Predict result: fertility_rate=${predictRes.data.fertility_rate}, model_version=${predictRes.data.model_version}`);
    
    if (!predictRes.data.fertility_rate || !predictRes.data.model_version) {
      throw new Error(`Missing fertility_rate or model_version in response`);
    }
    console.log(`[ok] All API endpoints working`);

  } catch (err) {
    console.error(`[fail] ${err.message}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
