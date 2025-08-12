#!/usr/bin/env node
/**
 * Simple image build: just create placeholder URLs for testing
 * Fallback for when sharp/puppeteer are not available
 */

const fs = require('fs');
const path = require('path');

// Load image index
const indexPath = 'artifacts/images/index.json';
if (!fs.existsSync(indexPath)) {
  console.error('❌ No image index found. Run images-fetch first.');
  process.exit(1);
}

const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
const outDir = 'artifacts/images/out';

// Ensure output directories exist
['hero', 'card', 'thumb'].forEach(size => {
  fs.mkdirSync(path.join(outDir, size), { recursive: true });
});

/**
 * Create placeholder files for testing
 */
async function createPlaceholders() {
  console.log('📸 Creating image placeholders (simple mode)...');
  
  const ids = Object.keys(index);
  console.log(`   Processing ${ids.length} images...\n`);
  
  for (const id of ids) {
    // Create placeholder files for each size
    for (const size of ['hero', 'card', 'thumb']) {
      const placeholderPath = path.join(outDir, size, `${id}.jpg`);
      
      // Write a small text file as placeholder
      fs.writeFileSync(placeholderPath, `Placeholder image for ${id} (${size})`);
    }
    
    console.log(`  ✅ Created placeholders for ${id}`);
  }
  
  console.log(`\n✅ Placeholder generation complete!`);
  console.log(`   Output: ${outDir}/`);
  console.log(`   Note: Install sharp for actual image processing`);
}

// Run if called directly
if (require.main === module) {
  createPlaceholders().catch(error => {
    console.error('💥 Placeholder creation failed:', error);
    process.exit(1);
  });
}

module.exports = { createPlaceholders };
