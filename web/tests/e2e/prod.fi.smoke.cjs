#!/usr/bin/env node
/**
 * Finnish newswire smoke test for production
 * Usage: PROD_URL="https://api.paranoidmodels.com" node tests/e2e/prod.fi.smoke.cjs
 */

const https = require('https');
const http = require('http');

const PROD_URL = process.env.PROD_URL || 'http://localhost:5173';
const TIMEOUT = 15000; // 15 seconds

function makeRequest(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https:') ? https : http;
    const req = client.get(url, { timeout: TIMEOUT }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: data
        });
      });
    });
    
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timeout after ${TIMEOUT}ms`));
    });
    
    req.on('error', reject);
  });
}

async function testFinnishAPI() {
  console.log('🇫🇮 Testing Finnish newswire API...');
  
  try {
    const response = await makeRequest(`${PROD_URL}/newswire/fi`);
    
    if (response.status !== 200) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = JSON.parse(response.body);
    
    // Validate structure
    if (!data.items || !Array.isArray(data.items)) {
      throw new Error('Missing or invalid items array');
    }
    
    if (typeof data.total !== 'number') {
      throw new Error('Missing or invalid total count');
    }
    
    if (data.origin_country_filter !== 'FI') {
      throw new Error(`Expected origin_country_filter=FI, got ${data.origin_country_filter}`);
    }
    
    console.log(`✅ API returned ${data.items.length} Finnish items`);
    
    // Validate Finnish items
    if (data.items.length > 0) {
      const item = data.items[0];
      const required = ['id', 'title', 'kicker', 'lede', 'origin_country'];
      const finnish = ['local_fi', 'local_fi_score'];
      
      for (const field of required) {
        if (!item[field]) {
          throw new Error(`Missing required field: ${field}`);
        }
      }
      
      if (item.origin_country !== 'FI') {
        throw new Error(`Expected origin_country=FI, got ${item.origin_country}`);
      }
      
      for (const field of finnish) {
        if (!(field in item)) {
          throw new Error(`Missing Finnish field: ${field}`);
        }
      }
      
      if (typeof item.local_fi_score !== 'number' || 
          item.local_fi_score < 0 || 
          item.local_fi_score > 1) {
        throw new Error(`Invalid local_fi_score: ${item.local_fi_score}`);
      }
      
      console.log(`✅ Finnish content validation passed`);
      console.log(`   - Source: ${item.source_name}`);
      console.log(`   - Relevance: ${Math.round(item.local_fi_score * 100)}%`);
    }
    
    return true;
    
  } catch (error) {
    console.error(`❌ Finnish API test failed: ${error.message}`);
    return false;
  }
}

async function testFinnishUI() {
  console.log('🇫🇮 Testing Finnish UI page...');
  
  try {
    const response = await makeRequest(`${PROD_URL}/newswire/fi`);
    
    if (response.status !== 200) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const html = response.body;
    
    // Basic HTML structure checks
    if (!html.includes('<html')) {
      throw new Error('Not a valid HTML page');
    }
    
    if (!html.includes('PARANOID Models')) {
      throw new Error('Missing page title');
    }
    
    console.log('✅ Finnish UI page loads successfully');
    console.log(`   - Content length: ${html.length} bytes`);
    
    return true;
    
  } catch (error) {
    console.error(`❌ Finnish UI test failed: ${error.message}`);
    return false;
  }
}

async function testGlobalAPIFilter() {
  console.log('🌍 Testing global API with Finnish filter...');
  
  try {
    const response = await makeRequest(`${PROD_URL}/newswire?origin_country=FI`);
    
    if (response.status !== 200) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = JSON.parse(response.body);
    
    if (data.origin_country_filter !== 'FI') {
      throw new Error(`Filter not applied: ${data.origin_country_filter}`);
    }
    
    console.log('✅ Global API Finnish filter works');
    
    return true;
    
  } catch (error) {
    console.error(`❌ Global API filter test failed: ${error.message}`);
    return false;
  }
}

async function runSmokeTests() {
  console.log(`🚀 Starting Finnish newswire smoke tests`);
  console.log(`   Target: ${PROD_URL}`);
  console.log(`   Timeout: ${TIMEOUT}ms\n`);
  
  const tests = [
    testFinnishAPI,
    testFinnishUI,
    testGlobalAPIFilter
  ];
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    try {
      const result = await test();
      if (result) {
        passed++;
      } else {
        failed++;
      }
    } catch (error) {
      console.error(`❌ Test error: ${error.message}`);
      failed++;
    }
    console.log(''); // Empty line between tests
  }
  
  console.log('📊 Test Results:');
  console.log(`   ✅ Passed: ${passed}`);
  console.log(`   ❌ Failed: ${failed}`);
  console.log(`   📈 Success rate: ${Math.round(passed / (passed + failed) * 100)}%`);
  
  if (failed > 0) {
    console.log('\n🚨 Some tests failed. Check the deployment.');
    process.exit(1);
  } else {
    console.log('\n🎉 All Finnish newswire tests passed!');
    process.exit(0);
  }
}

if (require.main === module) {
  runSmokeTests().catch(error => {
    console.error('💥 Smoke test runner crashed:', error.message);
    process.exit(1);
  });
}
