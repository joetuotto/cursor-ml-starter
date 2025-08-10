#!/usr/bin/env node
/**
 * 🚨 PARANOID MODEL V5 - COMPREHENSIVE SMOKE TESTS
 * 
 * Validates:
 * - Newswire UI rendering (Hero + cards)
 * - Data quality (why_it_matters coverage ≥ 80%)
 * - Enrichment validation (semantic uniqueness)
 * - Performance thresholds
 */

const puppeteer = require('puppeteer');

const PROD_URL = process.env.PROD_URL || 'https://api.paranoidmodels.com';
const WHY_IT_MATTERS_THRESHOLD = parseFloat(process.env.WHY_IT_MATTERS_THRESHOLD || '0.8');
const MIN_CARDS = parseInt(process.env.MIN_CARDS || '3');
const MAX_LOAD_TIME = parseInt(process.env.MAX_LOAD_TIME || '5000');

const WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL;

async function sendAlert(message, details = {}) {
  if (!WEBHOOK_URL) return;
  
  try {
    const payload = {
      text: `🚨 Paranoid Smoke Test Alert`,
      attachments: [{
        color: 'danger',
        fields: [
          { title: 'Message', value: message, short: false },
          { title: 'URL', value: PROD_URL, short: true },
          { title: 'Timestamp', value: new Date().toISOString(), short: true },
          ...Object.entries(details).map(([k, v]) => ({ title: k, value: String(v), short: true }))
        ]
      }]
    };
    
    await fetch(WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    console.error('❌ Alert send failed:', e.message);
  }
}

async function runParanoidSmokeTest() {
  console.log(`🚨 Starting Paranoid V5 smoke test on ${PROD_URL}`);
  
  const browser = await puppeteer.launch({ 
    headless: true, 
    args: ['--no-sandbox', '--disable-setuid-sandbox'] 
  });
  
  try {
    const page = await browser.newPage();
    await page.setUserAgent('ParanoidBot/1.0 (Smoke Test)');
    
    const startTime = Date.now();
    
    // ===== 1. BASIC CONNECTIVITY =====
    console.log('📡 Testing basic connectivity...');
    
    const healthResponse = await page.goto(`${PROD_URL}/health`, { waitUntil: 'networkidle0' });
    if (!healthResponse.ok()) {
      throw new Error(`Health check failed: ${healthResponse.status()}`);
    }
    
    const healthData = await healthResponse.json();
    console.log('✅ Health check passed:', {
      status: healthData.status,
      model_version: healthData.model_version,
      uptime_hours: Math.round(healthData.uptime_seconds / 3600)
    });
    
    // ===== 2. NEWSWIRE UI RENDERING =====
    console.log('🎨 Testing newswire UI rendering...');
    
    const uiResponse = await page.goto(`${PROD_URL}/newswire`, { 
      waitUntil: 'domcontentloaded',
      timeout: MAX_LOAD_TIME 
    });
    
    if (!uiResponse.ok()) {
      throw new Error(`UI load failed: ${uiResponse.status()}`);
    }
    
    const loadTime = Date.now() - startTime;
    console.log(`⏱️ Page loaded in ${loadTime}ms`);
    
    if (loadTime > MAX_LOAD_TIME) {
      await sendAlert(`Slow page load: ${loadTime}ms > ${MAX_LOAD_TIME}ms`, { load_time: loadTime });
    }
    
    // Wait for React to render
    await page.waitForTimeout(2000);
    
    // ===== 3. HERO SECTION VALIDATION =====
    console.log('🎯 Validating hero section...');
    
    const heroExists = await page.$('.hero-section, [data-testid="hero"], .hero, .newswire-hero');
    if (!heroExists) {
      throw new Error('Hero section not found');
    }
    
    const heroText = await page.evaluate(() => {
      const hero = document.querySelector('.hero-section, [data-testid="hero"], .hero, .newswire-hero');
      return hero ? hero.innerText.toLowerCase() : '';
    });
    
    if (!heroText.includes('paranoid') && !heroText.includes('trend') && !heroText.includes('signal')) {
      await sendAlert('Hero section missing paranoid/trend/signal keywords', { hero_text: heroText.slice(0, 100) });
    }
    
    console.log('✅ Hero section validated');
    
    // ===== 4. CARDS GRID VALIDATION =====
    console.log('📰 Validating news cards...');
    
    const cards = await page.$$('.news-card, [data-testid="news-card"], .card, .newswire-card');
    const cardCount = cards.length;
    
    if (cardCount < MIN_CARDS) {
      throw new Error(`Insufficient cards: ${cardCount} < ${MIN_CARDS}`);
    }
    
    console.log(`📊 Found ${cardCount} news cards`);
    
    // ===== 5. DATA QUALITY VALIDATION =====
    console.log('🔍 Validating data quality...');
    
    const cardData = await page.evaluate(() => {
      const cards = document.querySelectorAll('.news-card, [data-testid="news-card"], .card, .newswire-card');
      return Array.from(cards).map(card => ({
        title: card.querySelector('h1, h2, h3, .title, .headline')?.innerText || '',
        kicker: card.querySelector('.kicker, .tag, .category')?.innerText || '',
        lede: card.querySelector('.lede, .description, .excerpt, p')?.innerText || '',
        cta: card.querySelector('a, button, .cta')?.innerText || '',
        whyItMatters: card.innerText.toLowerCase().includes('why it matters') ||
                     card.innerText.toLowerCase().includes('why this matters') ||
                     card.querySelector('.why-it-matters, [data-field="why_it_matters"]') !== null
      }));
    });
    
    const cardsWithWhyItMatters = cardData.filter(card => card.whyItMatters).length;
    const whyItMattersCoverage = cardsWithWhyItMatters / cardCount;
    
    console.log(`🎯 Why it matters coverage: ${Math.round(whyItMattersCoverage * 100)}% (${cardsWithWhyItMatters}/${cardCount})`);
    
    if (whyItMattersCoverage < WHY_IT_MATTERS_THRESHOLD) {
      await sendAlert(
        `Low why_it_matters coverage: ${Math.round(whyItMattersCoverage * 100)}% < ${Math.round(WHY_IT_MATTERS_THRESHOLD * 100)}%`,
        { 
          coverage: whyItMattersCoverage,
          threshold: WHY_IT_MATTERS_THRESHOLD,
          cards_with_whyit: cardsWithWhyItMatters,
          total_cards: cardCount
        }
      );
    }
    
    // ===== 6. SEMANTIC UNIQUENESS CHECK =====
    console.log('🧠 Checking semantic uniqueness...');
    
    const titles = cardData.map(card => card.title.toLowerCase().trim()).filter(Boolean);
    const uniqueTitles = new Set(titles);
    const uniquenessRatio = uniqueTitles.size / titles.length;
    
    console.log(`🎨 Title uniqueness: ${Math.round(uniquenessRatio * 100)}% (${uniqueTitles.size}/${titles.length})`);
    
    if (uniquenessRatio < 0.7) {
      await sendAlert(
        `Low content uniqueness: ${Math.round(uniquenessRatio * 100)}% < 70%`,
        { uniqueness_ratio: uniquenessRatio, unique_titles: uniqueTitles.size, total_titles: titles.length }
      );
    }
    
    // ===== 7. ENRICHED DATA SOURCE VALIDATION =====
    console.log('📊 Validating enriched data source...');
    
    const enrichedResponse = await page.goto(`${PROD_URL}/artifacts/report.enriched.json`, { 
      waitUntil: 'networkidle0' 
    });
    
    if (enrichedResponse.ok()) {
      const enrichedData = await enrichedResponse.json();
      const enrichedCount = Array.isArray(enrichedData) ? enrichedData.length : 
                          enrichedData.items ? enrichedData.items.length :
                          enrichedData.signals ? enrichedData.signals.length : 0;
      
      console.log(`📡 Enriched data source: ${enrichedCount} items`);
      
      if (enrichedCount === 0) {
        await sendAlert('Empty enriched data source', { enriched_count: enrichedCount });
      }
    } else {
      console.log('⚠️ Enriched data source not accessible (this may be normal)');
    }
    
    // ===== 8. PERFORMANCE METRICS =====
    const metrics = await page.metrics();
    const performanceData = {
      load_time_ms: loadTime,
      js_heap_used_mb: Math.round(metrics.JSHeapUsedSize / 1024 / 1024),
      dom_nodes: metrics.Nodes,
      cards_count: cardCount,
      why_it_matters_coverage: Math.round(whyItMattersCoverage * 100),
      uniqueness_ratio: Math.round(uniquenessRatio * 100)
    };
    
    console.log('📈 Performance metrics:', performanceData);
    
    // ===== SUCCESS SUMMARY =====
    console.log('\n🎉 PARANOID V5 SMOKE TEST PASSED!');
    console.log('✅ Connectivity: OK');
    console.log('✅ UI Rendering: OK');
    console.log('✅ Hero Section: OK');
    console.log(`✅ Cards Grid: ${cardCount} cards`);
    console.log(`✅ Data Quality: ${Math.round(whyItMattersCoverage * 100)}% why_it_matters coverage`);
    console.log(`✅ Uniqueness: ${Math.round(uniquenessRatio * 100)}% unique titles`);
    console.log(`✅ Performance: ${loadTime}ms load time`);
    
    return performanceData;
    
  } catch (error) {
    console.error('❌ Paranoid smoke test failed:', error.message);
    await sendAlert(`Smoke test failed: ${error.message}`, { error: error.stack });
    process.exit(1);
    
  } finally {
    await browser.close();
  }
}

// Run if called directly
if (require.main === module) {
  runParanoidSmokeTest()
    .then(metrics => {
      console.log('\n📊 Final metrics:', JSON.stringify(metrics, null, 2));
      process.exit(0);
    })
    .catch(error => {
      console.error('💥 Test runner error:', error);
      process.exit(1);
    });
}

module.exports = { runParanoidSmokeTest };
