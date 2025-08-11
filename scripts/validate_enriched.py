#!/usr/bin/env python3
"""
Validation script for enriched content quality
"""

import json
import sys
import argparse
from pathlib import Path
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))
from prompts.enrich_fi import validate_enrichment, FORBIDDEN_PHRASES

def validate_file(input_file: str, schema_file: str = None) -> dict:
    """Validate enriched JSON file"""
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Failed to read JSON: {e}"],
            'file': input_file
        }
    
    # Handle both single item and array
    items = data if isinstance(data, list) else [data]
    if isinstance(data, dict) and 'items' in data:
        items = data['items']
    
    results = {
        'file': input_file,
        'total_items': len(items),
        'valid_items': 0,
        'invalid_items': 0,
        'errors': [],
        'warnings': [],
        'stats': {
            'avg_lede_length': 0,
            'avg_analysis_words': 0,
            'avg_numbers_per_item': 0,
            'finnish_items': 0
        }
    }
    
    total_lede_len = 0
    total_analysis_words = 0
    total_numbers = 0
    
    for i, item in enumerate(items):
        origin_country = item.get('origin_country')
        validation_result = validate_enrichment(item, origin_country)
        
        if validation_result['valid']:
            results['valid_items'] += 1
        else:
            results['invalid_items'] += 1
            for error in validation_result['errors']:
                results['errors'].append(f"Item {i+1}: {error}")
        
        # Collect stats
        lede_len = len(item.get('lede', ''))
        total_lede_len += lede_len
        
        analysis_words = validation_result.get('word_count', 0)
        total_analysis_words += analysis_words
        
        numbers = validation_result.get('number_count', 0)
        total_numbers += numbers
        
        if origin_country == 'FI':
            results['stats']['finnish_items'] += 1
        
        # Additional warnings
        if lede_len > 400:
            results['warnings'].append(f"Item {i+1}: Lede too long ({lede_len} chars)")
        
        if analysis_words > 1200:
            results['warnings'].append(f"Item {i+1}: Analysis very long ({analysis_words} words)")
        
        # Check for repetitive content
        title = item.get('title', '').lower()
        lede = item.get('lede', '').lower()
        if title and lede and title[:30] in lede:
            results['warnings'].append(f"Item {i+1}: Lede appears to repeat headline")
    
    # Calculate averages
    if len(items) > 0:
        results['stats']['avg_lede_length'] = round(total_lede_len / len(items))
        results['stats']['avg_analysis_words'] = round(total_analysis_words / len(items))
        results['stats']['avg_numbers_per_item'] = round(total_numbers / len(items), 1)
    
    results['valid'] = results['invalid_items'] == 0
    
    return results

def print_validation_report(results: dict, verbose: bool = False):
    """Print formatted validation report"""
    
    print(f"\n📊 Validation Report: {results['file']}")
    print("=" * 50)
    
    # Overall status
    status_icon = "✅" if results['valid'] else "❌"
    print(f"{status_icon} Overall: {'VALID' if results['valid'] else 'INVALID'}")
    print(f"📈 Items: {results['valid_items']}/{results['total_items']} valid")
    
    # Stats
    stats = results['stats']
    print(f"\n📋 Statistics:")
    print(f"  • Average lede length: {stats['avg_lede_length']} chars")
    print(f"  • Average analysis: {stats['avg_analysis_words']} words")
    print(f"  • Numbers per item: {stats['avg_numbers_per_item']}")
    print(f"  • Finnish items: {stats['finnish_items']}")
    
    # Errors
    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Limit to first 10
            print(f"  • {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")
    
    # Warnings
    if results['warnings'] and verbose:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings'][:5]:
            print(f"  • {warning}")
        if len(results['warnings']) > 5:
            print(f"  ... and {len(results['warnings']) - 5} more")
    
    print()

def main():
    parser = argparse.ArgumentParser(description="Validate enriched content quality")
    parser.add_argument("input", help="JSON file to validate")
    parser.add_argument("--schema", help="JSON schema file (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show warnings")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)
    
    results = validate_file(args.input, args.schema)
    
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_validation_report(results, args.verbose)
    
    # Exit with error code if validation failed
    sys.exit(0 if results['valid'] else 1)

if __name__ == "__main__":
    main()