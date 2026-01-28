"""
Deep analysis of HTML content to find price patterns.
This script searches for any price-like text in the raw HTML.
"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup

TEST_URLS = {
    'Al-Fatah': 'https://alfatah.pk/products/youngs-choco-bliss-peanut-cocoa-spread-glass-jar-350gm',
    'Metro': 'https://www.metro-online.pk/detail/cooking-essentials/commodities/flour/punjab-atta-no.1-10kg-(pg)/16446559?categoryName=Search',
    'Carrefour': 'https://www.carrefour.pk/mafpak/en/vegetable-ghee/tullo-banaspati-pouch-1kg/p/38092',
    'Imtiaz': 'https://shop.imtiaz.com.pk/product/tapal-tea-tezdum-900g-367900',
    'Rainbow': 'https://rainbowcc.com.pk/product/prema-yogurt-vanilla-2147691',
    'Jalal Sons': 'https://jalalsons.com.pk/product/nutro-wafer-vanilla-150g-177868'
}

def fetch_page(url: str) -> str:
    """Fetch page with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    response = requests.get(url, headers=headers, timeout=15)
    return response.text

def find_price_patterns(html: str) -> list:
    """Find price patterns using regex."""
    patterns = [
        r'Rs\.?\s*\d{1,5}[,\d]*\.?\d*',  # Rs. 1234 or Rs1234
        r'PKR\s*\d{1,5}[,\d]*\.?\d*',     # PKR 1234
        r'\d{1,5}[,\d]*\.?\d*\s*Rs',       # 1234 Rs
        r'price["\']:\s*["\']?\d+',        # "price": "1234" (JSON)
        r'"price"\s*:\s*\d+',              # "price": 1234
    ]

    findings = []
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches[:5]:  # Limit to 5 per pattern
            findings.append((pattern, match))

    return findings

def check_for_json_data(html: str) -> dict:
    """Check if prices are in JSON/Script tags (common in React apps)."""
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script')

    json_scripts = []
    for script in scripts:
        if script.string:
            # Look for common patterns indicating price data
            if any(keyword in script.string for keyword in ['price', 'product', 'data']):
                # Find JSON-like structures
                json_matches = re.findall(r'\{[^{}]*"[^"]*price[^"]*"[^{}]*\}', script.string, re.IGNORECASE)
                if json_matches:
                    json_scripts.extend(json_matches[:2])  # Limit output

    return {'json_count': len(json_scripts), 'samples': json_scripts[:3]}

def analyze_store(store: str, url: str):
    """Analyze a single store's HTML content."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {store}")
    print(f"{'='*70}")

    try:
        html = fetch_page(url)
        print(f"✅ Fetched {len(html):,} characters")

        # 1. Search for price patterns
        print(f"\n--- Price Pattern Search ---")
        price_findings = find_price_patterns(html)

        if price_findings:
            print(f"✅ Found {len(price_findings)} price patterns:")
            seen = set()
            for pattern, match in price_findings:
                if match not in seen:
                    print(f"   - {match}")
                    seen.add(match)
        else:
            print("⚠️  No price patterns found")

        # 2. Check for JSON/Script data
        print(f"\n--- JSON/Script Data Check ---")
        json_info = check_for_json_data(html)
        if json_info['json_count'] > 0:
            print(f"✅ Found {json_info['json_count']} JSON structures with 'price'")
            for sample in json_info['samples']:
                print(f"   Sample: {sample[:100]}...")
        else:
            print("⚠️  No JSON price data found")

        # 3. Look for React/SPA indicators
        print(f"\n--- SPA Detection ---")
        spa_indicators = {
            'react': 'react' in html.lower(),
            'next.js': 'next' in html.lower() and 'data' in html.lower(),
            'angular': 'ng-app' in html or 'angular' in html.lower(),
            'vue': 'vue' in html.lower(),
            'hydration': '__NEXT_DATA__' in html or '__NUXT__' in html,
            'empty_content': len(html.strip()) < 1000
        }

        any_spa = any(spa_indicators.values())
        if any_spa:
            print("⚠️  SPA indicators found (prices may need JavaScript):")
            for indicator, found in spa_indicators.items():
                if found:
                    print(f"   - {indicator}")
        else:
            print("✅ No strong SPA indicators detected")

        # 4. Recommendation
        print(f"\n--- Recommendation ---")
        if price_findings and not any_spa:
            print("✅ CAN USE HTTP - Prices found in HTML, no SPA detected")
            return 'HTTP_OK'
        elif price_findings:
            print("⚠️  UNCERTAIN - Prices found but SPA detected, may need JS")
            return 'UNCERTAIN'
        elif json_info['json_count'] > 0:
            print("⚠️  MAYBE - Price data in JSON, can parse without browser")
            return 'JSON_OK'
        else:
            print("❌ NEEDS SELENIUM - No price data in initial HTML")
            return 'NEEDS_SELENIUM'

    except Exception as e:
        print(f"❌ Error: {e}")
        return 'ERROR'

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║              DEEP HTML CONTENT ANALYSIS FOR PRICES                  ║
║                                                                      ║
║  This script analyzes raw HTML to determine if prices are present    ║
║  without needing JavaScript execution.                               ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    results = {}
    for store, url in TEST_URLS.items():
        result = analyze_store(store, url)
        results[store] = result

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")

    categories = {
        'HTTP_OK': '✅ Can use HTTP (prices in HTML)',
        'JSON_OK': '📊 Can use HTTP + JSON parsing',
        'UNCERTAIN': '⚠️  Uncertain (needs testing)',
        'NEEDS_SELENIUM': '❌ Needs Selenium',
        'ERROR': '❌ Error fetching'
    }

    for category, description in categories.items():
        stores = [s for s, r in results.items() if r == category]
        if stores:
            print(f"\n{description}:")
            for store in stores:
                print(f"   - {store}")

if __name__ == "__main__":
    main()
