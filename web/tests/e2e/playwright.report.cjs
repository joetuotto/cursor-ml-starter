#!/usr/bin/env node
/**
 * 🎭 PLAYWRIGHT HTML REPORT GENERATOR
 * 
 * Generates comprehensive HTML reports for paranoid newswire testing
 * with screenshots, performance metrics, and quality validation.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const PROD_URL = process.env.PROD_URL || 'https://api.paranoidmodels.com';
const REPORT_DIR = process.env.REPORT_DIR || 'test-reports';
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-');

class PlaywrightReportGenerator {
  constructor() {
    this.reportData = {
      timestamp: new Date().toISOString(),
      url: PROD_URL,
      tests: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        warnings: 0
      },
      performance: {},
      screenshots: []
    };
    
    this.reportDir = path.join(REPORT_DIR, `paranoid-${TIMESTAMP}`);
    this.screenshotDir = path.join(this.reportDir, 'screenshots');
  }

  async init() {
    // Create report directories
    await fs.promises.mkdir(this.reportDir, { recursive: true });
    await fs.promises.mkdir(this.screenshotDir, { recursive: true });
  }

  async takeScreenshot(page, name, fullPage = false) {
    const filename = `${name}-${Date.now()}.png`;
    const filepath = path.join(this.screenshotDir, filename);
    
    await page.screenshot({ 
      path: filepath, 
      fullPage,
      type: 'png'
    });
    
    this.reportData.screenshots.push({
      name,
      filename,
      path: `screenshots/${filename}`,
      timestamp: new Date().toISOString()
    });
    
    return filepath;
  }

  async runTest(name, testFn) {
    console.log(`🧪 Running test: ${name}`);
    
    const testResult = {
      name,
      status: 'running',
      startTime: Date.now(),
      endTime: null,
      duration: null,
      error: null,
      warnings: [],
      metrics: {},
      screenshots: []
    };

    try {
      const result = await testFn();
      testResult.status = 'passed';
      testResult.metrics = result.metrics || {};
      testResult.warnings = result.warnings || [];
      
      this.reportData.summary.passed++;
      if (result.warnings && result.warnings.length > 0) {
        this.reportData.summary.warnings += result.warnings.length;
      }
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.error = {
        message: error.message,
        stack: error.stack
      };
      this.reportData.summary.failed++;
      console.error(`❌ Test failed: ${name}`, error.message);
    }

    testResult.endTime = Date.now();
    testResult.duration = testResult.endTime - testResult.startTime;
    
    this.reportData.tests.push(testResult);
    this.reportData.summary.total++;
    
    return testResult;
  }

  async runFullSuite() {
    console.log(`🎭 Starting Playwright test suite for ${PROD_URL}`);
    
    await this.init();
    
    const browser = await puppeteer.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
      const page = await browser.newPage();
      await page.setUserAgent('PlaywrightBot/1.0 (Test Suite)');
      
      // Set viewport for consistent screenshots
      await page.setViewport({ width: 1920, height: 1080 });

      // Test 1: Health Check
      await this.runTest('Health Check', async () => {
        const response = await page.goto(`${PROD_URL}/health`, { waitUntil: 'networkidle0' });
        
        if (!response.ok()) {
          throw new Error(`Health check failed: ${response.status()}`);
        }
        
        const healthData = await response.json();
        
        return {
          metrics: {
            status: healthData.status,
            uptime_hours: Math.round(healthData.uptime_seconds / 3600),
            model_version: healthData.model_version
          }
        };
      });

      // Test 2: UI Load Performance
      await this.runTest('UI Load Performance', async () => {
        const startTime = Date.now();
        
        const response = await page.goto(`${PROD_URL}/newswire`, { 
          waitUntil: 'domcontentloaded',
          timeout: 10000
        });
        
        const loadTime = Date.now() - startTime;
        
        if (!response.ok()) {
          throw new Error(`UI load failed: ${response.status()}`);
        }
        
        // Wait for React to render
        await page.waitForTimeout(2000);
        
        // Take screenshot of initial load
        await this.takeScreenshot(page, 'ui-initial-load', true);
        
        const warnings = [];
        if (loadTime > 5000) {
          warnings.push(`Slow load time: ${loadTime}ms`);
        }
        
        return {
          metrics: {
            load_time_ms: loadTime,
            status_code: response.status()
          },
          warnings
        };
      });

      // Test 3: Hero Section Validation
      await this.runTest('Hero Section Validation', async () => {
        const heroElement = await page.$('.hero-section, [data-testid="hero"], .hero, .newswire-hero');
        
        if (!heroElement) {
          throw new Error('Hero section not found');
        }
        
        const heroText = await page.evaluate(() => {
          const hero = document.querySelector('.hero-section, [data-testid="hero"], .hero, .newswire-hero');
          return hero ? hero.innerText.toLowerCase() : '';
        });
        
        await this.takeScreenshot(page, 'hero-section');
        
        const hasKeywords = ['paranoid', 'trend', 'signal', 'intelligence'].some(
          keyword => heroText.includes(keyword)
        );
        
        const warnings = [];
        if (!hasKeywords) {
          warnings.push('Hero section missing key paranoid/intelligence keywords');
        }
        
        return {
          metrics: {
            hero_text_length: heroText.length,
            has_keywords: hasKeywords
          },
          warnings
        };
      });

      // Test 4: News Cards Validation
      await this.runTest('News Cards Validation', async () => {
        const cards = await page.$$('.news-card, [data-testid="news-card"], .card, .newswire-card');
        const cardCount = cards.length;
        
        if (cardCount === 0) {
          throw new Error('No news cards found');
        }
        
        // Extract card data
        const cardData = await page.evaluate(() => {
          const cards = document.querySelectorAll('.news-card, [data-testid="news-card"], .card, .newswire-card');
          return Array.from(cards).map((card, index) => ({
            index,
            title: card.querySelector('h1, h2, h3, .title, .headline')?.innerText || '',
            kicker: card.querySelector('.kicker, .tag, .category')?.innerText || '',
            lede: card.querySelector('.lede, .description, .excerpt, p')?.innerText || '',
            whyItMatters: card.innerText.toLowerCase().includes('why it matters') ||
                         card.innerText.toLowerCase().includes('why this matters') ||
                         card.querySelector('.why-it-matters, [data-field="why_it_matters"]') !== null
          }));
        });
        
        // Take screenshot of cards grid
        await this.takeScreenshot(page, 'news-cards-grid', true);
        
        const cardsWithWhyItMatters = cardData.filter(card => card.whyItMatters).length;
        const whyItMattersCoverage = cardsWithWhyItMatters / cardCount;
        
        const titles = cardData.map(card => card.title.toLowerCase().trim()).filter(Boolean);
        const uniqueTitles = new Set(titles);
        const uniquenessRatio = uniqueTitles.size / titles.length;
        
        const warnings = [];
        if (whyItMattersCoverage < 0.8) {
          warnings.push(`Low why_it_matters coverage: ${Math.round(whyItMattersCoverage * 100)}%`);
        }
        if (uniquenessRatio < 0.7) {
          warnings.push(`Low content uniqueness: ${Math.round(uniquenessRatio * 100)}%`);
        }
        if (cardCount < 3) {
          warnings.push(`Few cards detected: ${cardCount}`);
        }
        
        return {
          metrics: {
            total_cards: cardCount,
            cards_with_why_it_matters: cardsWithWhyItMatters,
            why_it_matters_coverage: Math.round(whyItMattersCoverage * 100),
            unique_titles: uniqueTitles.size,
            uniqueness_ratio: Math.round(uniquenessRatio * 100)
          },
          warnings
        };
      });

      // Test 5: Data Source Validation
      await this.runTest('Data Source Validation', async () => {
        const enrichedResponse = await page.goto(`${PROD_URL}/artifacts/report.enriched.json`, { 
          waitUntil: 'networkidle0' 
        });
        
        const warnings = [];
        let metrics = {
          data_source_accessible: enrichedResponse.ok(),
          enriched_items: 0
        };
        
        if (enrichedResponse.ok()) {
          const enrichedData = await enrichedResponse.json();
          const enrichedCount = Array.isArray(enrichedData) ? enrichedData.length : 
                              enrichedData.items ? enrichedData.items.length :
                              enrichedData.signals ? enrichedData.signals.length : 0;
          
          metrics.enriched_items = enrichedCount;
          
          if (enrichedCount === 0) {
            warnings.push('Empty enriched data source');
          }
        } else {
          warnings.push('Enriched data source not accessible');
        }
        
        return { metrics, warnings };
      });

      // Test 6: Performance Metrics
      await this.runTest('Performance Metrics', async () => {
        const metrics = await page.metrics();
        const performanceEntries = await page.evaluate(() => {
          return JSON.parse(JSON.stringify(performance.getEntriesByType('navigation')));
        });
        
        const nav = performanceEntries[0] || {};
        
        return {
          metrics: {
            js_heap_used_mb: Math.round(metrics.JSHeapUsedSize / 1024 / 1024),
            dom_nodes: metrics.Nodes,
            dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd - nav.domContentLoadedEventStart),
            load_complete_ms: Math.round(nav.loadEventEnd - nav.loadEventStart)
          }
        };
      });

      // Store overall performance data
      const finalMetrics = await page.metrics();
      this.reportData.performance = {
        total_test_duration_ms: Date.now() - this.reportData.tests[0].startTime,
        final_js_heap_mb: Math.round(finalMetrics.JSHeapUsedSize / 1024 / 1024),
        total_dom_nodes: finalMetrics.Nodes
      };

    } finally {
      await browser.close();
    }

    await this.generateHTMLReport();
    return this.reportData;
  }

  async generateHTMLReport() {
    const htmlTemplate = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paranoid Newswire Test Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #f8fafc; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header .meta { opacity: 0.8; }
        
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .summary-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .summary-card h3 { color: #64748b; font-size: 0.875rem; text-transform: uppercase; margin-bottom: 0.5rem; }
        .summary-card .value { font-size: 2rem; font-weight: bold; }
        .passed { color: #16a34a; }
        .failed { color: #dc2626; }
        .warnings { color: #d97706; }
        
        .test-section { background: white; border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .test-item { border-bottom: 1px solid #e2e8f0; padding: 1rem 0; }
        .test-item:last-child { border-bottom: none; }
        .test-header { display: flex; justify-content: between; align-items: center; margin-bottom: 1rem; }
        .test-name { font-size: 1.125rem; font-weight: 600; }
        .test-status { padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 500; }
        .status-passed { background: #dcfce7; color: #166534; }
        .status-failed { background: #fecaca; color: #991b1b; }
        .test-duration { color: #64748b; font-size: 0.875rem; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin: 1rem 0; }
        .metric { background: #f8fafc; padding: 1rem; border-radius: 6px; }
        .metric-label { color: #64748b; font-size: 0.875rem; }
        .metric-value { font-weight: 600; }
        
        .warnings-list { margin: 1rem 0; }
        .warning-item { background: #fef3c7; color: #92400e; padding: 0.5rem 1rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 4px solid #f59e0b; }
        
        .error-details { background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 1rem; margin: 1rem 0; }
        .error-message { color: #991b1b; font-weight: 600; margin-bottom: 0.5rem; }
        .error-stack { color: #dc2626; font-family: monospace; font-size: 0.875rem; white-space: pre-wrap; }
        
        .screenshots-section { margin-top: 2rem; }
        .screenshots-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
        .screenshot-item { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .screenshot-item img { width: 100%; height: auto; display: block; }
        .screenshot-meta { padding: 1rem; }
        .screenshot-name { font-weight: 600; margin-bottom: 0.25rem; }
        .screenshot-time { color: #64748b; font-size: 0.875rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Paranoid Newswire Test Report</h1>
            <div class="meta">
                <div>URL: ${this.reportData.url}</div>
                <div>Generated: ${new Date(this.reportData.timestamp).toLocaleString()}</div>
                <div>Duration: ${this.reportData.performance.total_test_duration_ms}ms</div>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">${this.reportData.summary.total}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value passed">${this.reportData.summary.passed}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value failed">${this.reportData.summary.failed}</div>
            </div>
            <div class="summary-card">
                <h3>Warnings</h3>
                <div class="value warnings">${this.reportData.summary.warnings}</div>
            </div>
        </div>
        
        <div class="test-section">
            <h2>Test Results</h2>
            ${this.reportData.tests.map(test => `
                <div class="test-item">
                    <div class="test-header">
                        <div class="test-name">${test.name}</div>
                        <div>
                            <span class="test-status status-${test.status}">${test.status.toUpperCase()}</span>
                            <span class="test-duration">${test.duration}ms</span>
                        </div>
                    </div>
                    
                    ${Object.keys(test.metrics).length > 0 ? `
                        <div class="metrics-grid">
                            ${Object.entries(test.metrics).map(([key, value]) => `
                                <div class="metric">
                                    <div class="metric-label">${key.replace(/_/g, ' ')}</div>
                                    <div class="metric-value">${value}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${test.warnings.length > 0 ? `
                        <div class="warnings-list">
                            ${test.warnings.map(warning => `
                                <div class="warning-item">⚠️ ${warning}</div>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${test.error ? `
                        <div class="error-details">
                            <div class="error-message">❌ ${test.error.message}</div>
                            <div class="error-stack">${test.error.stack}</div>
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
        
        ${this.reportData.screenshots.length > 0 ? `
            <div class="screenshots-section">
                <div class="test-section">
                    <h2>Screenshots</h2>
                    <div class="screenshots-grid">
                        ${this.reportData.screenshots.map(screenshot => `
                            <div class="screenshot-item">
                                <img src="${screenshot.path}" alt="${screenshot.name}" />
                                <div class="screenshot-meta">
                                    <div class="screenshot-name">${screenshot.name}</div>
                                    <div class="screenshot-time">${new Date(screenshot.timestamp).toLocaleString()}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        ` : ''}
    </div>
</body>
</html>
    `;

    const reportPath = path.join(this.reportDir, 'index.html');
    await fs.promises.writeFile(reportPath, htmlTemplate);
    
    // Also save JSON data
    const jsonPath = path.join(this.reportDir, 'report.json');
    await fs.promises.writeFile(jsonPath, JSON.stringify(this.reportData, null, 2));
    
    console.log(`📄 HTML report generated: ${reportPath}`);
    console.log(`📊 JSON data saved: ${jsonPath}`);
    
    return reportPath;
  }
}

// Run if called directly
if (require.main === module) {
  const reporter = new PlaywrightReportGenerator();
  
  reporter.runFullSuite()
    .then(reportData => {
      console.log('\n🎉 Test suite completed!');
      console.log(`📊 Results: ${reportData.summary.passed}/${reportData.summary.total} passed`);
      if (reportData.summary.warnings > 0) {
        console.log(`⚠️ Warnings: ${reportData.summary.warnings}`);
      }
      
      process.exit(reportData.summary.failed > 0 ? 1 : 0);
    })
    .catch(error => {
      console.error('💥 Test suite error:', error);
      process.exit(1);
    });
}

module.exports = { PlaywrightReportGenerator };
