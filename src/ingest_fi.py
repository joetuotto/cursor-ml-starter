#!/usr/bin/env python3
"""
Finnish news ingest sources
Scrapes RSS feeds and normalizes data for enrichment pipeline
"""

import os
import time
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import feedparser
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinnishNewsIngest:
    """Ingest news from Finnish sources"""
    
    def __init__(self):
        self.sources = {
            "YLE": {
                "rss_url": "https://feeds.yle.fi/uutiset/v1/majorNews/YLE_UUTISET/fi.rss",
                "source_url": "https://yle.fi",
                "categories": ["uutiset", "talous", "politiikka"]
            },
            "HS": {
                "rss_url": "https://www.hs.fi/rss/tuoreimmat.xml",
                "source_url": "https://hs.fi",
                "categories": ["talous", "politiikka", "kotimaa"]
            },
            "Kauppalehti": {
                "rss_url": "https://www.kauppalehti.fi/rss/tuoreimmat",
                "source_url": "https://kauppalehti.fi",
                "categories": ["talous", "yritykset", "markkinat"]
            },
            "Talouselämä": {
                "rss_url": "https://www.talouselama.fi/rss/all",
                "source_url": "https://talouselama.fi", 
                "categories": ["talous", "yritykset", "teknologia"]
            },
            "Ilta-Sanomat": {
                "rss_url": "https://www.is.fi/rss/tuoreimmat.xml",
                "source_url": "https://is.fi",
                "categories": ["uutiset", "talous", "kotimaa"]
            }
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Paranoid Models Feed Aggregator (contact@paranoidmodels.com)'
        })
    
    def normalize_category(self, title: str, description: str, source_name: str) -> str:
        """Guess category based on content and source"""
        content = f"{title} {description}".lower()
        
        # Business/Economy keywords
        if any(word in content for word in [
            'korko', 'pankki', 'talous', 'euro', 'osake', 'sijoitus', 
            'yritys', 'kauppa', 'vero', 'inflaatio', 'euribor', 'börs'
        ]):
            return "talous"
        
        # Politics keywords  
        if any(word in content for word in [
            'hallitus', 'eduskunta', 'ministeri', 'presidentti', 'vaali',
            'politiikka', 'laki', 'päätös', 'kunta', 'kaupunki'
        ]):
            return "politiikka"
            
        # Technology keywords
        if any(word in content for word in [
            'teknologia', 'digitaali', 'tekoäly', 'data', 'verkko',
            'sovellus', 'ohjelmisto', 'startup', 'innovaatio'
        ]):
            return "teknologia"
            
        # Energy keywords
        if any(word in content for word in [
            'energia', 'sähkö', 'öljy', 'kaasu', 'tuuli', 'ydin',
            'hiili', 'lämpö', 'bensa', 'polttoaine'
        ]):
            return "energia"
            
        # Company/Business based on source
        if source_name in ["Kauppalehti", "Talouselämä"]:
            return "yritykset"
            
        return "other"
    
    def create_content_hash(self, title: str, url: str, published: str) -> str:
        """Create unique ID for content"""
        content = f"{title}:{url}:{published}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def parse_feed(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Parse RSS feed and return normalized items"""
        items = []
        
        try:
            logger.info(f"Fetching feed: {source_name}")
            response = self.session.get(source_config["rss_url"], timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:15]:  # Limit to latest 15 items
                try:
                    # Parse published date
                    published_dt = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    else:
                        published_dt = datetime.now(timezone.utc)
                    
                    # Extract content
                    title = entry.get('title', '').strip()
                    summary = entry.get('summary', '').strip()
                    link = entry.get('link', '')
                    
                    if not title or not link:
                        continue
                        
                    # Clean summary from HTML
                    if summary:
                        soup = BeautifulSoup(summary, 'html.parser')
                        summary = soup.get_text().strip()
                    
                    # Create normalized item
                    item = {
                        "id": f"fi-{source_name.lower()}-{self.create_content_hash(title, link, published_dt.isoformat())}",
                        "title": title,
                        "source_name": source_name,
                        "source_url": link,
                        "published_at": published_dt.isoformat(),
                        "origin_country": "FI",
                        "summary_raw": summary if summary else "",
                        "category_guess": self.normalize_category(title, summary, source_name),
                        "ingested_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error parsing entry from {source_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching feed {source_name}: {e}")
            
        return items
    
    def ingest_all(self) -> List[Dict]:
        """Ingest from all configured sources"""
        all_items = []
        
        for source_name, config in self.sources.items():
            try:
                items = self.parse_feed(source_name, config)
                all_items.extend(items)
                logger.info(f"Ingested {len(items)} items from {source_name}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to ingest {source_name}: {e}")
                
        # Remove duplicates based on title similarity
        unique_items = self.deduplicate_items(all_items)
        logger.info(f"Total unique items: {len(unique_items)}")
        
        return unique_items
    
    def deduplicate_items(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate items based on title similarity"""
        seen_titles = set()
        unique_items = []
        
        for item in items:
            title_lower = item["title"].lower()
            # Simple deduplication - could be improved with similarity scoring
            title_key = title_lower[:50]  # First 50 chars
            
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
                
        return unique_items

def main():
    """CLI interface for Finnish news ingest"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest Finnish news sources")
    parser.add_argument("--output", "-o", default="artifacts/signal.fi.json", 
                       help="Output file for ingested items")
    parser.add_argument("--limit", "-l", type=int, default=50,
                       help="Maximum items to output")
    
    args = parser.parse_args()
    
    ingest = FinnishNewsIngest()
    items = ingest.ingest_all()
    
    # Limit output
    if args.limit:
        items = items[:args.limit]
    
    # Save to file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump({
            "items": items,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "total_count": len(items),
            "sources": list(ingest.sources.keys())
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(items)} items to {args.output}")

if __name__ == "__main__":
    main()
