#!/usr/bin/env python3
"""
Update feeds with image data from image index
"""
import json
import os
import hashlib
from pathlib import Path

FEEDS_DIR = Path("artifacts/feeds")
IMAGES_INDEX = Path("artifacts/images/index.json")
BUCKET = os.getenv("BUCKET", "paranoidmodels.com")

def generate_image_id(headline, lang):
    """Generate same ID as images_fetch.py"""
    return hashlib.md5(
        (headline + lang).encode()
    ).hexdigest()[:12]

def update_feed_with_images(feed_path):
    """Add image data to feed items"""
    if not feed_path.exists():
        print(f"Feed not found: {feed_path}")
        return
        
    if not IMAGES_INDEX.exists():
        print(f"Image index not found: {IMAGES_INDEX}")
        return
        
    # Load data
    feed_data = json.loads(feed_path.read_text())
    image_index = json.loads(IMAGES_INDEX.read_text())
    
    items = feed_data if isinstance(feed_data, list) else feed_data.get("items", [])
    updated_count = 0
    
    for item in items:
        # Generate image ID
        lang = item.get("lang", "en")
        headline = item.get("headline", "")
        img_id = generate_image_id(headline, lang)
        
        # Add image ID to item
        item["id"] = img_id
        
        # Check if image exists
        if img_id in image_index:
            image_meta = image_index[img_id]
            
            # Add image URLs
            item["image"] = {
                "hero": f"https://storage.googleapis.com/{BUCKET}/newswire/img/hero/{img_id}.jpg",
                "card": f"https://storage.googleapis.com/{BUCKET}/newswire/img/card/{img_id}.jpg", 
                "thumb": f"https://storage.googleapis.com/{BUCKET}/newswire/img/thumb/{img_id}.jpg",
                "attribution": {
                    "author": image_meta.get("author", "Unknown"),
                    "source_url": image_meta.get("source_url", ""),
                    "license": image_meta.get("license", "CC-BY"),
                    "license_url": image_meta.get("license_url", "")
                }
            }
            
            # Add OG image
            item["og_image"] = f"https://storage.googleapis.com/{BUCKET}/newswire/og/{img_id}.png"
            updated_count += 1
        else:
            print(f"  No image found for: {headline[:50]}...")
    
    # Save updated feed
    feed_path.write_text(json.dumps(feed_data, ensure_ascii=False, indent=2))
    print(f"✅ Updated {feed_path.name}: {updated_count}/{len(items)} items with images")

def main():
    """Update all feeds with image data"""
    print("📸 Adding image data to feeds...")
    
    for lang in ("en", "fi"):
        feed_path = FEEDS_DIR / f"trends.{lang}.json"
        update_feed_with_images(feed_path)
    
    print("\n✅ Feed image update complete!")

if __name__ == "__main__":
    main()
