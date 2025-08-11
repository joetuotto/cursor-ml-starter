#!/usr/bin/env python3
"""
Images fetch: free sources (Openverse + Wikimedia Commons)
No API keys required
"""
import json
import os
import pathlib
import requests
import urllib.parse
import hashlib
import re

OUT_DIR = pathlib.Path("artifacts/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RAW = OUT_DIR / "raw"
RAW.mkdir(exist_ok=True, parents=True)
INDEX = OUT_DIR / "index.json"

def openverse_search(q, limit=3):
    """Search Openverse for CC0/CC-BY images"""
    url = "https://api.openverse.engineering/v1/images/"
    params = {
        "q": q,
        "license_type": "cc0,cc-by",
        "page_size": limit,
        "aspect_ratio": "wide",
        "mature": "false",
        "size": "medium,large"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"Openverse search failed for '{q}': {e}")
        return []

def wikimedia_search(q, limit=2):
    """Fallback to Wikimedia Commons"""
    try:
        search_url = "https://commons.wikimedia.org/w/api.php"
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"filetype:bitmap {q}",
            "srnamespace": 6,  # File namespace
            "srlimit": limit
        }
        
        r = requests.get(search_url, params=search_params, timeout=15)
        r.raise_for_status()
        results = []
        
        for item in r.json().get("query", {}).get("search", []):
            title = item["title"]
            # Get image info
            info_params = {
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": 1200
            }
            
            info_r = requests.get(search_url, params=info_params, timeout=10)
            info_data = info_r.json()
            
            for page in info_data.get("query", {}).get("pages", {}).values():
                if "imageinfo" in page:
                    img_info = page["imageinfo"][0]
                    meta = img_info.get("extmetadata", {})
                    
                    # Check if it's free license
                    license_name = meta.get("LicenseShortName", {}).get("value", "")
                    if any(term in license_name.lower() for term in ["cc", "public domain", "pd"]):
                        results.append({
                            "url": img_info.get("url", ""),
                            "thumburl": img_info.get("thumburl", img_info.get("url", "")),
                            "creator": meta.get("Artist", {}).get("value", "Wikimedia Commons"),
                            "license": license_name,
                            "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                            "source": "wikimedia"
                        })
                        break
        
        return results[:limit]
    except Exception as e:
        print(f"Wikimedia search failed for '{q}': {e}")
        return []

def build_keywords(item):
    """Extract keywords from news item"""
    keywords = []
    
    # Topic/category
    if item.get("topic"):
        keywords.append(item["topic"])
    
    # Country context
    country = item.get("country", "")
    if country == "FI":
        keywords.extend(["finland", "helsinki", "business"])
    elif country == "EU":
        keywords.extend(["europe", "brussels", "finance"])
    elif country == "US":
        keywords.extend(["america", "business", "finance"])
    
    # Extract entities from headline/analysis
    text = f"{item.get('headline', '')} {item.get('analysis', '')}"
    
    # Financial terms
    if any(term in text.lower() for term in ["bank", "rate", "interest", "fed", "ecb"]):
        keywords.extend(["banking", "finance", "economy"])
    
    # Technology terms  
    if any(term in text.lower() for term in ["tech", "ai", "startup", "funding"]):
        keywords.extend(["technology", "innovation", "computer"])
    
    # Generic business fallbacks
    keywords.extend(["business", "office", "meeting"])
    
    return keywords

def pick_for_card(item):
    """Select best image for a news card"""
    keywords = build_keywords(item)
    
    # Try multiple keyword combinations
    queries = [
        " ".join(keywords[:3]),  # Top 3 keywords
        " ".join(keywords[:2]),  # Top 2 keywords  
        keywords[0] if keywords else "business",  # Single keyword
        item.get("headline", "")[:50]  # Part of headline
    ]
    
    for query in queries:
        if not query.strip():
            continue
            
        # Try Openverse first
        results = openverse_search(query, 2)
        for res in results:
            if res.get("url") and res.get("creator"):
                return {
                    "source": "openverse",
                    "source_url": res.get("foreign_landing_url", res["url"]),
                    "author": res.get("creator") or "Unknown",
                    "license": res.get("license", "CC-BY"),
                    "license_url": res.get("license_url", ""),
                    "raw_url": res["url"],
                    "query": query
                }
        
        # Fallback to Wikimedia
        results = wikimedia_search(query, 1)
        for res in results:
            if res.get("url"):
                return {
                    "source": "wikimedia", 
                    "source_url": res["url"],
                    "author": res.get("creator", "Wikimedia Commons"),
                    "license": res.get("license", "CC-BY"),
                    "license_url": res.get("license_url", ""),
                    "raw_url": res.get("thumburl", res["url"]),
                    "query": query
                }
    
    # Ultimate fallback - abstract business image search
    fallback_results = openverse_search("abstract business technology", 1)
    if fallback_results:
        res = fallback_results[0]
        return {
            "source": "openverse",
            "source_url": res.get("foreign_landing_url", res["url"]),
            "author": res.get("creator") or "Unknown", 
            "license": res.get("license", "CC-BY"),
            "license_url": res.get("license_url", ""),
            "raw_url": res["url"],
            "query": "fallback"
        }
    
    return None

def download_image(url, dst):
    """Download image with proper headers"""
    headers = {
        "User-Agent": "ParanoidNewswire/1.0 (newswire bot; legal use)"
    }
    
    try:
        with requests.get(url, stream=True, timeout=30, headers=headers) as r:
            r.raise_for_status()
            with open(dst, "wb") as f:
                for chunk in r.iter_content(1 << 15):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return False

def main(feed_path):
    """Process a feed file and download images"""
    if not os.path.exists(feed_path):
        print(f"Feed not found: {feed_path}")
        return
        
    data = json.load(open(feed_path))
    items = data if isinstance(data, list) else data.get("items", [])
    
    index = {}
    
    for item in items:
        # Generate stable ID
        card_id = hashlib.md5(
            (item.get("headline", "") + item.get("lang", "")).encode()
        ).hexdigest()[:12]
        
        print(f"Processing: {item.get('headline', 'Unknown')[:50]}...")
        
        meta = pick_for_card(item)
        if not meta:
            print(f"  No image found for {card_id}")
            continue
            
        # Download image
        raw_file = RAW / f"{card_id}.jpg"
        if download_image(meta["raw_url"], raw_file):
            meta["raw_path"] = str(raw_file)
            meta["id"] = card_id
            index[card_id] = meta
            print(f"  ✅ Downloaded from {meta['source']}: {meta['author']}")
        else:
            print(f"  ❌ Download failed for {card_id}")
    
    # Save index
    json.dump(index, open(INDEX, "w"), ensure_ascii=False, indent=2)
    print(f"\n✅ Processed {len(index)} images → {INDEX}")

if __name__ == "__main__":
    # Process both language feeds
    for lang in ("en", "fi"):
        feed_path = f"artifacts/feeds/trends.{lang}.json"
        if os.path.exists(feed_path):
            print(f"\n📥 Processing {lang.upper()} feed...")
            main(feed_path)
