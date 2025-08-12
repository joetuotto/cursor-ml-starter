#!/usr/bin/env node
/**
 * Simple OG image generator: creates text placeholders
 * Fallback for when puppeteer/canvas are not available
 */

const fs = require('fs');
const path = require('path');

const outDir = 'artifacts/images/og';
fs.mkdirSync(outDir, { recursive: true });

/**
 * Create placeholder OG files
 */
async function createOGPlaceholders() {
  console.log('🎭 Creating OG image placeholders (simple mode)...');
  
  // Load feeds
  const items = [];
  for (const lang of ['en', 'fi']) {
    const feedPath = `artifacts/feeds/trends.${lang}.json`;
    if (fs.existsSync(feedPath)) {
      const data = JSON.parse(fs.readFileSync(feedPath, 'utf8'));
      const feedItems = Array.isArray(data) ? data : data.items || [];
      
      // Add IDs to items
      feedItems.forEach((item, index) => {
        if (!item.id) {
          const headline = item.headline || `item-${index}`;
          item.id = headline.slice(0, 40).replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
        }
      });
      
      items.push(...feedItems);
    }
  }
  
  if (items.length === 0) {
    console.log('⚠️  No feed items found. Run feeds generation first.');
    return;
  }
  
  console.log(`   Processing ${items.length} items...`);
  
  for (const item of items) {
    const id = item.id || 'unknown';
    
    // Create simple text placeholder
    const placeholder = `OG Image Placeholder
${item.kicker || 'ANALYSIS'}
${item.headline || 'No headline'}
Generated: ${new Date().toISOString()}`;
    
    const outputPath = path.join(outDir, `${id}.png`);
    fs.writeFileSync(outputPath, placeholder);
    
    console.log(`  ✅ Created OG placeholder: ${id}.png`);
  }
  
  console.log(`\n✅ OG placeholder generation complete!`);
  console.log(`   Output: ${outDir}/`);
  console.log(`   Note: Install puppeteer for actual OG images`);
}

// Run if called directly
if (require.main === module) {
  createOGPlaceholders().catch(error => {
    console.error('💥 OG placeholder creation failed:', error);
    process.exit(1);
  });
}

module.exports = { createOGPlaceholders };
