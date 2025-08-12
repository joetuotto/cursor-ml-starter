#!/usr/bin/env node
/**
 * Images build: duotone + vignette processing 
 * Creates hero/card/thumb sizes with brand styling
 */

const fs = require('fs');
const sharp = require('sharp');
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

// Brand colors from environment or defaults
const brandColor = process.env.IMG_BRAND_COLOR || '#59D3A2';
const bgColor = process.env.IMG_BG_COLOR || '#0E0E12';
const grainAmount = parseFloat(process.env.IMG_GRAIN || '0.03');

// Size configurations
const sizes = {
  hero: [1600, 900],
  card: [1200, 630], 
  thumb: [400, 225]
};

/**
 * Create vignette overlay SVG
 */
function createVignette(width, height) {
  return Buffer.from(`
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
          <stop offset="0%" style="stop-color:black;stop-opacity:0" />
          <stop offset="70%" style="stop-color:black;stop-opacity:0.1" />
          <stop offset="100%" style="stop-color:black;stop-opacity:0.4" />
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#vignette)" />
    </svg>
  `);
}

/**
 * Add film grain effect
 */
function addGrain(img, width, height) {
  // Create noise buffer
  const noiseSize = Math.min(width, height, 800); // Limit for performance
  const noiseBuffer = Buffer.alloc(noiseSize * noiseSize);
  
  for (let i = 0; i < noiseBuffer.length; i++) {
    noiseBuffer[i] = Math.random() * 255;
  }
  
  const noise = sharp(noiseBuffer, {
    raw: { width: noiseSize, height: noiseSize, channels: 1 }
  })
    .resize(width, height)
    .toFormat('png');
    
  return img.composite([{
    input: noise,
    blend: 'overlay',
    opacity: grainAmount
  }]);
}

/**
 * Process single image to all sizes
 */
async function processImage(id, meta) {
  const rawPath = meta.raw_path;
  
  if (!fs.existsSync(rawPath)) {
    console.log(`⚠️ Raw image not found: ${rawPath}`);
    return;
  }
  
  console.log(`🎨 Processing ${id}...`);
  
  for (const [sizeName, [width, height]] of Object.entries(sizes)) {
    try {
      let img = sharp(rawPath)
        .resize(width, height, {
          fit: 'cover',
          position: 'center'
        });
      
      // Apply duotone effect
      // 1. Desaturate and increase contrast
      img = img
        .modulate({
          saturation: 0.3,  // Heavy desaturation
          brightness: 1.1,  // Slight brightness boost
          hue: 0            // No hue shift
        })
        .linear(1.2, -(256 * 0.1)); // Increase contrast
      
      // 2. Apply brand color tint
      img = img.tint(brandColor);
      
      // 3. Add dark background overlay
      const darkOverlay = Buffer.from(`
        <svg width="${width}" height="${height}">
          <rect width="100%" height="100%" fill="${bgColor}" opacity="0.25"/>
        </svg>
      `);
      
      img = img.composite([{
        input: darkOverlay,
        blend: 'multiply'
      }]);
      
      // 4. Add vignette
      const vignette = createVignette(width, height);
      img = img.composite([{
        input: vignette,
        blend: 'multiply'
      }]);
      
      // 5. Add subtle grain (only for larger sizes)
      if (width >= 800) {
        img = addGrain(img, width, height);
      }
      
      // 6. Final adjustments and save
      await img
        .jpeg({
          quality: 85,
          mozjpeg: true,
          progressive: true
        })
        .toFile(path.join(outDir, sizeName, `${id}.jpg`));
        
    } catch (error) {
      console.error(`❌ Failed to process ${sizeName} for ${id}:`, error.message);
    }
  }
  
  console.log(`  ✅ Created hero/card/thumb for ${id}`);
}

/**
 * Main processing function
 */
async function main() {
  console.log('🎨 Building styled images with duotone + vignette...');
  console.log(`   Brand: ${brandColor} | Background: ${bgColor} | Grain: ${grainAmount}`);
  
  const ids = Object.keys(index);
  console.log(`   Processing ${ids.length} images...\n`);
  
  // Process images sequentially to avoid memory issues
  for (const id of ids) {
    await processImage(id, index[id]);
  }
  
  console.log(`\n✅ Image processing complete!`);
  console.log(`   Output: ${outDir}/`);
  console.log(`   Sizes: ${Object.keys(sizes).join(', ')}`);
}

// Check dependencies
try {
  require('sharp');
} catch (error) {
  console.error('❌ Sharp not found. Install with: npm install sharp');
  process.exit(1);
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('💥 Build failed:', error);
    process.exit(1);
  });
}

module.exports = { processImage, main };
