#!/usr/bin/env node
/**
 * OG image generator: social media cards with headlines
 * Creates 1200x630 images for Open Graph sharing
 */

const fs = require('fs');
const path = require('path');

// Try puppeteer, fallback to basic canvas approach
let puppeteer;
try {
  puppeteer = require('puppeteer');
} catch (e) {
  console.log('ℹ️  Puppeteer not found, will try canvas fallback');
}

const outDir = 'artifacts/images/og';
fs.mkdirSync(outDir, { recursive: true });

// Brand colors
const brandColor = process.env.IMG_BRAND_COLOR || '#59D3A2';
const bgColor = process.env.IMG_BG_COLOR || '#0E0E12';

/**
 * Generate HTML template for OG image
 */
function generateHTML(kicker, headline, date = new Date().toLocaleDateString()) {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      width: 1200px;
      height: 630px;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
      background: linear-gradient(135deg, ${bgColor} 0%, #1a1a1f 100%);
      color: #ffffff;
      overflow: hidden;
      position: relative;
    }
    
    .container {
      position: relative;
      width: 100%;
      height: 100%;
      padding: 60px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    
    .grain-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-image: 
        radial-gradient(circle at 25% 25%, rgba(255,255,255,0.02) 1px, transparent 1px),
        radial-gradient(circle at 75% 75%, rgba(255,255,255,0.015) 1px, transparent 1px);
      background-size: 50px 50px, 80px 80px;
      pointer-events: none;
      opacity: 0.3;
    }
    
    .content {
      z-index: 2;
      position: relative;
    }
    
    .kicker {
      font-size: 22px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: ${brandColor};
      margin-bottom: 24px;
      opacity: 0.95;
    }
    
    .headline {
      font-size: 64px;
      font-weight: 700;
      line-height: 1.1;
      max-width: 1000px;
      margin-bottom: 32px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .meta {
      position: absolute;
      bottom: 40px;
      right: 60px;
      display: flex;
      align-items: center;
      gap: 20px;
      font-size: 18px;
      font-weight: 500;
      opacity: 0.8;
    }
    
    .date {
      color: #a0a0a0;
    }
    
    .logo {
      color: ${brandColor};
      font-weight: 600;
    }
    
    /* Responsive text sizing */
    @media (max-width: 1200px) {
      .headline { font-size: 56px; }
    }
  </style>
</head>
<body>
  <div class="grain-overlay"></div>
  <div class="container">
    <div class="content">
      <div class="kicker">${kicker || 'ANALYSIS'}</div>
      <div class="headline">${headline}</div>
    </div>
    <div class="meta">
      <span class="date">${date}</span>
      <span class="logo">PARANOID NEWSWIRE</span>
    </div>
  </div>
</body>
</html>`;
}

/**
 * Generate OG image using Puppeteer
 */
async function generateWithPuppeteer(items) {
  console.log('🎭 Generating OG images with Puppeteer...');
  
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    headless: 'new'
  });
  
  const page = await browser.newPage();
  await page.setViewport({ 
    width: 1200, 
    height: 630, 
    deviceScaleFactor: 2 // High DPI for crisp text
  });
  
  for (const item of items) {
    const id = item.id || item.headline?.slice(0, 40).replace(/\s+/g, '-') || 'unknown';
    const html = generateHTML(item.kicker, item.headline);
    
    try {
      await page.setContent(html, { waitUntil: 'networkidle0' });
      
      const outputPath = path.join(outDir, `${id}.png`);
      await page.screenshot({ 
        path: outputPath,
        type: 'png',
        quality: 90
      });
      
      console.log(`  ✅ Generated OG image: ${id}.png`);
    } catch (error) {
      console.error(`  ❌ Failed to generate OG for ${id}:`, error.message);
    }
  }
  
  await browser.close();
}

/**
 * Canvas-based fallback (requires node-canvas)
 */
async function generateWithCanvas(items) {
  console.log('🎨 Generating OG images with Canvas (fallback)...');
  
  let Canvas;
  try {
    Canvas = require('canvas');
  } catch (e) {
    console.error('❌ Neither puppeteer nor canvas available. Install one of them:');
    console.error('   npm install puppeteer  # OR');
    console.error('   npm install canvas');
    process.exit(1);
  }
  
  for (const item of items) {
    const id = item.id || item.headline?.slice(0, 40).replace(/\s+/g, '-') || 'unknown';
    
    try {
      const canvas = Canvas.createCanvas(1200, 630);
      const ctx = canvas.getContext('2d');
      
      // Background gradient
      const gradient = ctx.createLinearGradient(0, 0, 1200, 630);
      gradient.addColorStop(0, bgColor);
      gradient.addColorStop(1, '#1a1a1f');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 1200, 630);
      
      // Kicker
      ctx.font = '600 22px Inter, sans-serif';
      ctx.fillStyle = brandColor;
      ctx.fillText((item.kicker || 'ANALYSIS').toUpperCase(), 60, 120);
      
      // Headline (with word wrapping)
      ctx.font = '700 64px Inter, sans-serif';
      ctx.fillStyle = '#ffffff';
      
      const words = item.headline?.split(' ') || ['No headline'];
      const maxWidth = 1000;
      let line = '';
      let y = 200;
      const lineHeight = 70;
      
      for (const word of words) {
        const testLine = line + word + ' ';
        const metrics = ctx.measureText(testLine);
        
        if (metrics.width > maxWidth && line !== '') {
          ctx.fillText(line, 60, y);
          line = word + ' ';
          y += lineHeight;
          if (y > 400) break; // Max 3 lines
        } else {
          line = testLine;
        }
      }
      ctx.fillText(line, 60, y);
      
      // Meta info
      ctx.font = '500 18px Inter, sans-serif';
      ctx.fillStyle = '#a0a0a0';
      ctx.fillText(new Date().toLocaleDateString(), 1000, 580);
      
      ctx.fillStyle = brandColor;
      ctx.fillText('PARANOID NEWSWIRE', 850, 605);
      
      // Save
      const outputPath = path.join(outDir, `${id}.png`);
      const buffer = canvas.toBuffer('image/png');
      fs.writeFileSync(outputPath, buffer);
      
      console.log(`  ✅ Generated OG image: ${id}.png`);
    } catch (error) {
      console.error(`  ❌ Failed to generate OG for ${id}:`, error.message);
    }
  }
}

/**
 * Main function
 */
async function main() {
  console.log('📱 Generating Open Graph images...');
  
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
  
  // Try Puppeteer first, fallback to Canvas
  if (puppeteer) {
    await generateWithPuppeteer(items);
  } else {
    await generateWithCanvas(items);
  }
  
  console.log(`\n✅ OG image generation complete!`);
  console.log(`   Output: ${outDir}/`);
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('💥 OG generation failed:', error);
    process.exit(1);
  });
}

module.exports = { main, generateHTML };
