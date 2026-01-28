"""
Test script to check if prices are server-side rendered for each store.
This helps determine if we can use requests + BeautifulSoup instead of Selenium.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse

# Test URLs from each store
TEST_URLS = {
    'Al-Fatah': 'https://alfatah.pk/products/youngs-choco-bliss-peanut-cocoa-spread-glass-jar-350gm',
    'Metro': 'https://www.metro-online.pk/detail/cooking-essentials/commodities/flour/punjab-atta-no.1-10kg-(pg)/16446559?categoryName=Search',
    'Carrefour': 'https://www.carrefour.pk/mafpak/en/vegetable-ghee/tullo-banaspati-pouch-1kg/p/38092',
    'Imtiaz': 'https://shop.imtiaz.com.pk/product/tapal-tea-tezdum-900g-367900',
    'Rainbow': 'https://rainbowcc.com.pk/product/prema-yogurt-vanilla-2147691',
    'Jalal Sons': 'https://jalalsons.com.pk/product/nutro-wafer-vanilla-150g-177868'
}

# Store-specific selectors for price detection
STORE_SELECTORS = {
    'Al-Fatah': [
        '.product-price',
        '.price',
        '[class*="price"]',
        '.product-info .price'
    ],
    'Metro': [
        '.CategoryGrid_product_details_price__dNQQQ',
        '.product_details_price',
        '.price',
        '[class*="price"]'
    ],
    'Carrefour': [
        'div.text-xl.leading-7.font-bold',
        'div.text-2xl.leading-7.font-bold',
        '.product-price',
        '[class*="price"]'
    ],
    'Imtiaz': [
        '.MuiBox-root span',
        '.price',
        '[class*="price"]',
        'button span'
    ],
    'Rainbow': [
        '.price',
        '.product-price',
        '[class*="price"]'
    ],
    'Jalal Sons': [
        '.price',
        '.product-price',
        '[class*="price"]'
    ]
}

def fetch_page(url: str, timeout: int = 15) -> tuple[bool, str, str]:
    """Fetch page with proper headers to avoid bot detection."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return True, response.text, str(response.status_code)
    except requests.exceptions.Timeout:
        return False, "", "Timeout"
    except requests.exceptions.RequestException as e:
        return False, "", str(e)

def extract_prices_from_html(html: str, store: str) -> list:
    """Try to extract prices using store-specific selectors."""
    soup = BeautifulSoup(html, 'html.parser')
    found_prices = []

    selectors = STORE_SELECTORS.get(store, ['.price'])

    for selector in selectors:
        try:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                # Look for price patterns (Rs., PKR, numbers with decimals)
                if any(x in text for x in ['Rs.', 'PKR', 'Rs']) or any(c.isdigit() for c in text):
                    found_prices.append({
                        'selector': selector,
                        'text': text[:100]  # Truncate long text
                    })
        except Exception as e:
            continue

    return found_prices

def test_store(store_name: str, url: str) -> dict:
    """Test a single store for server-side price rendering."""
    print(f"\n{'='*60}")
    print(f"Testing: {store_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    # Fetch the page
    success, html, status = fetch_page(url)

    result = {
        'store': store_name,
        'url': url,
        'fetched': success,
        'status': status,
        'has_prices': False,
        'prices_found': [],
        'recommendation': 'Unknown'
    }

    if not success:
        print(f"❌ Failed to fetch: {status}")
        result['recommendation'] = 'BLOCKED - Needs Selenium'
        return result

    print(f"✅ Page fetched successfully (Status: {status})")
    print(f"   HTML length: {len(html):,} characters")

    # Try to extract prices
    prices = extract_prices_from_html(html, store_name)

    if prices:
        result['has_prices'] = True
        result['prices_found'] = prices
        result['recommendation'] = '✅ CAN USE HTTP - Prices in HTML'

        print(f"✅ Found {len(prices)} price elements:")
        for p in prices[:3]:  # Show first 3
            print(f"   - [{p['selector']}] {p['text']}")
        if len(prices) > 3:
            print(f"   ... and {len(prices) - 3} more")
    else:
        result['recommendation'] = '⚠️ UNCERTAIN - May need Selenium'
        print(f"⚠️  No prices found with known selectors")
        print(f"   (Prices may be loaded via JavaScript)")

    return result

def main():
    """Run tests on all stores."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                  HTTP FETCHING COMPATIBILITY TEST                  ║
║                                                                      ║
║  This script tests if store prices are server-side rendered.        ║
║  If prices are in HTML, we can use requests instead of Selenium.    ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    results = []

    for store, url in TEST_URLS.items():
        result = test_store(store, url)
        results.append(result)
        time.sleep(1)  # Rate limiting

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    can_use_http = [r for r in results if 'CAN USE' in r['recommendation']]
    uncertain = [r for r in results if 'UNCERTAIN' in r['recommendation']]
    blocked = [r for r in results if 'BLOCKED' in r['recommendation']]

    print(f"\n✅ Can use HTTP requests (Optimizable): {len(can_use_http)}")
    for r in can_use_http:
        print(f"   - {r['store']}")

    print(f"\n⚠️  Uncertain (May need Selenium): {len(uncertain)}")
    for r in uncertain:
        print(f"   - {r['store']}")

    print(f"\n❌ Blocked/Needs Selenium: {len(blocked)}")
    for r in blocked:
        print(f"   - {r['store']}")

    # Speed comparison estimate
    print(f"\n{'='*60}")
    print("ESTIMATED SPEED COMPARISON")
    print(f"{'='*60}")

    products_per_store = 100
    selenium_time = products_per_store * 4  # ~4 sec per product with Selenium
    http_time = products_per_store * 0.3    # ~0.3 sec per product with HTTP

    print(f"For {products_per_store} products per store:")
    print(f"  Selenium (current):  ~{selenium_time//60} minutes")
    print(f"  HTTP requests:        ~{int(http_time//60)} minutes")
    print(f"  Speed improvement:    ~{int(selenium_time/http_time)}x faster")

    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print("1. For 'CAN USE HTTP' stores: Rewrite updaters with requests + BeautifulSoup")
    print("2. For 'UNCERTAIN' stores: More testing needed, may need hybrid approach")
    print("3. For 'BLOCKED' stores: Continue using Selenium")

if __name__ == "__main__":
    main()
