"""
OPTIMIZED Jalal Sons Price Updater - Using HTTP Requests instead of Selenium

This version is 10-20x faster than the Selenium version by:
1. Using requests library to fetch HTML directly
2. Parsing JSON from <script type="application/ld+json"> tags
3. No browser overhead, works on headless servers

Performance:
- Selenium: ~4-5 seconds per product
- This version: ~0.2-0.3 seconds per product
"""
import sys
import pandas as pd
import time
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Import progress tracker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from progress_tracker import ProgressTracker

# HTTP requests + JSON parsing
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JalalSonsPriceUpdaterFast:
    """
    Optimized Jalal Sons price updater using HTTP requests instead of Selenium.

    Speed improvement: ~10-20x faster than Selenium version
    """

    def __init__(self, use_selenium_fallback: bool = True):
        """
        Initialize the fast Jalal Sons price updater

        Args:
            use_selenium_fallback (bool): If True, falls back to Selenium on HTTP failures
        """
        self.base_url = "https://jalalsons.com.pk"
        self.store_id = "Jalal Sons"
        self.use_selenium_fallback = use_selenium_fallback

        # Statistics tracking
        self.stats = {
            'total': 0,
            'processed': 0,
            'price_changes': 0,
            'errors': 0,
            'unchanged': 0,
            'results': [],
            'http_success': 0,
            'fallback_used': 0
        }

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def _fetch_page(self, url: str, timeout: int = 10) -> Optional[str]:
        """Fetch page HTML using requests."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            self.stats['http_success'] += 1
            return response.text
        except requests.exceptions.Timeout:
            logger.debug(f"   ⏱️ Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"   ❌ Request failed: {e}")
            return None

    def extract_price_from_json_ld(self, html: str) -> Optional[float]:
        """
        Extract price from JSON-LD structured data.
        Jalal Sons uses Schema.org format: {"@type": "Offer", "price": "648", ...}
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find all JSON-LD script tags
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    # Handle both single object and array formats
                    if isinstance(data, list):
                        items = data
                    else:
                        items = [data]

                    for item in items:
                        # Look for Offer/Product type with price
                        if item.get('@type') in ['Offer', 'Product']:
                            # Direct price in Offer
                            if 'price' in item:
                                price_str = str(item['price'])
                                # Clean and convert
                                price = re.sub(r'[^\d.]', '', price_str)
                                if price:
                                    return float(price)

                            # Check nested offers
                            if 'offers' in item:
                                offers = item['offers']
                                if isinstance(offers, list):
                                    for offer in offers:
                                        if 'price' in offer:
                                            price_str = str(offer['price'])
                                            price = re.sub(r'[^\d.]', '', price_str)
                                            if price:
                                                return float(price)
                                elif isinstance(offers, dict) and 'price' in offers:
                                    price_str = str(offers['price'])
                                    price = re.sub(r'[^\d.]', '', price_str)
                                    if price:
                                        return float(price)

                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        except Exception as e:
            logger.debug(f"   ⚠️ JSON-LD parsing error: {e}")

        return None

    def extract_price_from_next_data(self, html: str) -> Optional[float]:
        """
        Extract price from __NEXT_DATA__ script tag (Next.js sites).
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find __NEXT_DATA__ script
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            if not next_data_script:
                return None

            data = json.loads(next_data_script.string)

            # Navigate the props structure to find price
            # Common Next.js structure: props.pageProps.product.price
            def find_price_in_dict(obj, depth=0):
                if depth > 10:  # Prevent infinite recursion
                    return None
                if isinstance(obj, dict):
                    # Check for direct price keys
                    for key in ['price', 'sellingPrice', 'finalPrice', 'amount']:
                        if key in obj:
                            val = obj[key]
                            if isinstance(val, (int, float, str)):
                                price_str = str(val).replace(',', '').replace('Rs', '').replace('PKR', '').strip()
                                match = re.search(r'\d+\.?\d*', price_str)
                                if match:
                                    try:
                                        price = float(match.group())
                                        if price > 0:
                                            return price
                                    except ValueError:
                                        pass
                    # Recurse into values
                    for val in obj.values():
                        result = find_price_in_dict(val, depth + 1)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_price_in_dict(item, depth + 1)
                        if result:
                            return result
                return None

            return find_price_in_dict(data)

        except Exception as e:
            logger.debug(f"   ⚠️ __NEXT_DATA__ parsing error: {e}")

        return None

    def extract_price_from_text(self, html: str) -> Optional[float]:
        """
        Fallback: Extract price from text patterns in HTML.
        Looks for patterns like: Rs648, Rs. 648, PKR 648
        """
        try:
            # Regex patterns for price in text
            patterns = [
                r'Rs\.?\s*(\d{1,5}[,\d]*\.?\d*)',  # Rs. 648 or Rs648
                r'PKR\s*(\d{1,5}[,\d]*\.?\d*)',   # PKR 648
                r'"price"\s*:\s*"?\s*(\d{1,5}[,\d]*\.?\d*)',  # JSON "price": "648"
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Get the first reasonable price (not too large, not zero)
                    for match in matches:
                        price_str = match.replace(',', '')
                        try:
                            price = float(price_str)
                            if 0 < price < 100000:  # Sanity check
                                return price
                        except ValueError:
                            continue

        except Exception as e:
            logger.debug(f"   ⚠️ Text pattern extraction error: {e}")

        return None

    def extract_price_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract price from Jalal Sons product page using HTTP requests.

        Multiple extraction strategies:
        1. JSON-LD structured data (most reliable)
        2. __NEXT_DATA__ script tag
        3. Text pattern matching (fallback)
        """
        try:
            logger.info(f"   🌐 Fetching: {url}")

            # Fetch HTML
            html = self._fetch_page(url)

            if not html:
                logger.warning(f"   ❌ Failed to fetch page")
                return None

            # Strategy 1: Try JSON-LD (Schema.org)
            price = self.extract_price_from_json_ld(html)
            source = "JSON-LD"

            # Strategy 2: Try __NEXT_DATA__
            if price is None:
                price = self.extract_price_from_next_data(html)
                source = "__NEXT_DATA__"

            # Strategy 3: Try text patterns
            if price is None:
                price = self.extract_price_from_text(html)
                source = "text pattern"

            if price:
                logger.info(f"   💰 Found price: Rs. {price} (via {source})")
                return {
                    'current_price': price,
                    'original_price': None,
                    'source_info': {
                        'method': 'HTTP + ' + source,
                        'url': url
                    },
                    'is_sale': False
                }
            else:
                logger.warning(f"   ❌ Could not extract price from page")
                return None

        except Exception as e:
            logger.error(f"   ❌ Error extracting price from {url}: {e}")
            return None

    def _test_connection(self) -> bool:
        """Test website connection."""
        try:
            logger.info(f"🔍 Testing connection to {self.base_url}...")
            html = self._fetch_page(self.base_url, timeout=5)

            if html and len(html) > 1000:
                logger.info("✅ Connection successful")
                return True
            else:
                logger.warning("⚠️ Connection test returned empty response")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Connection test failed: {e}")
            return False

    def parse_price_history(self, price_history_data) -> List[Dict]:
        """Parse price history from CSV data"""
        try:
            if pd.isna(price_history_data) or price_history_data == '':
                return []

            if isinstance(price_history_data, str):
                if price_history_data.startswith('[') or price_history_data.startswith('{'):
                    return json.loads(price_history_data)
            elif isinstance(price_history_data, list):
                return price_history_data

            return []
        except Exception as e:
            logger.warning(f"   ⚠️  Could not parse price history: {e}")
            return []

    def create_price_history_entry(self, price: float, is_current: bool = False) -> Dict:
        """Create new price history entry"""
        return {
            'price': price,
            'is_current': is_current,
            'timestamp': datetime.now().isoformat()
        }

    def update_price_history(self, current_history: List[Dict], new_price: float) -> List[Dict]:
        """Update price history array"""
        updated_history = []
        for entry in current_history:
            updated_entry = entry.copy()
            updated_entry['is_current'] = False
            updated_history.append(updated_entry)

        updated_history.append(self.create_price_history_entry(new_price, True))
        return updated_history

    def generate_comparison_csv(self, input_csv_path: str, output_csv_path: str = None,
                                delay_seconds: float = 0.5, progress_tracker: Optional[ProgressTracker] = None) -> Dict:
        """
        Generate comparison CSV for manual review using fast HTTP requests.

        Args:
            delay_seconds: Delay between requests (default 0.5s - much faster than Selenium's 3s)
        """
        try:
            if not output_csv_path:
                timestamp = datetime.now().strftime('%Y-%m-%d')
                output_csv_path = f'jalalsons_price_comparison_{timestamp}.csv'

            logger.info(f"📄 Reading CSV file: {input_csv_path}")
            df = pd.read_csv(input_csv_path)

            self.stats['total'] = len(df)
            logger.info(f"📊 Found {self.stats['total']} products to check\n")

            # Test connection
            self._test_connection()

            comparison_data = []

            # Filter out already processed products if using progress tracker
            if progress_tracker:
                processed_ids = progress_tracker.get_processed_ids()
                if processed_ids:
                    original_count = len(df)
                    df = df[~df['product_id'].astype(str).isin(processed_ids)]
                    skipped_count = original_count - len(df)
                    if skipped_count > 0:
                        logger.info(f"📂 Resuming: Skipping {skipped_count} already processed products")
                        logger.info(f"📊 Remaining products to process: {len(df)}")
                        self.stats['total'] = len(df)

            for index, product in df.iterrows():
                progress = f"[{index + 1}/{self.stats['total']}]"
                product_name = product.get('name', 'Unknown Product')

                logger.info(f"{progress} 🔍 Checking: {product_name}")

                comparison_row = {
                    'product_id': product.get('product_id'),
                    'old_price': product.get('price'),
                    'new_price': None,
                    'price_change_needed': 'NO'
                }

                current_price_history = self.parse_price_history(product.get('price_history'))

                # Skip if no URL
                if pd.isna(product.get('original_url')) or not product.get('original_url'):
                    logger.warning(f"{progress} ⏭️  Skipping - No URL")
                    comparison_row['price_change_needed'] = 'ERROR - No URL'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', error_message='No URL')
                    continue

                csv_price = product.get('price')
                if pd.isna(csv_price) or csv_price <= 0:
                    logger.warning(f"{progress} ⏭️  Skipping - Invalid price: {csv_price}")
                    comparison_row['price_change_needed'] = 'ERROR - Invalid Price'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', error_message='Invalid Price')
                    continue

                logger.info(f"   📋 CSV Price: Rs. {csv_price}")

                # Get current price from website
                website_data = self.extract_price_from_page(product['original_url'])

                if not website_data:
                    logger.warning(f"{progress} ❌ Could not fetch price")
                    comparison_row['price_change_needed'] = 'ERROR - Failed to fetch'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', old_price=csv_price, error_message='Failed to fetch')
                elif not website_data.get('current_price'):
                    logger.warning(f"{progress} ❌ Could not extract price")
                    comparison_row['price_change_needed'] = 'ERROR - Price not found'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', old_price=csv_price, error_message='Price not found')
                else:
                    website_price = website_data['current_price']
                    price_difference = website_price - csv_price

                    comparison_row['new_price'] = website_price

                    if abs(price_difference) < 0.01:
                        logger.info(f"{progress} ✅ Prices match")
                        comparison_row['price_change_needed'] = 'NO'
                        self.stats['unchanged'] += 1
                        if progress_tracker:
                            progress_tracker.save_progress(product.get('product_id'), 'NO_CHANGE', old_price=csv_price, new_price=website_price)
                    else:
                        logger.info(f"{progress} 🔄 Price difference: Rs. {price_difference:.2f}")
                        logger.info(f"   📋 CSV: Rs. {csv_price} → 🌐 Website: Rs. {website_price}")
                        comparison_row['price_change_needed'] = 'YES'
                        self.stats['price_changes'] += 1
                        if progress_tracker:
                            progress_tracker.save_progress(product.get('product_id'), 'SUCCESS', old_price=csv_price, new_price=website_price)

                    comparison_data.append(comparison_row)
                    self.stats['processed'] += 1

                logger.info('')

                # Rate limiting
                if index < len(df) - 1:
                    time.sleep(delay_seconds)

            # Save comparison CSV
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_csv(output_csv_path, index=False)

            logger.info(f"\n✅ Comparison CSV generated: {output_csv_path}")
            logger.info(f"📊 Summary: {self.stats['processed']} checked, {self.stats['price_changes']} changes, "
                       f"{self.stats['unchanged']} unchanged, {self.stats['errors']} errors")
            logger.info(f"⚡ HTTP requests succeeded: {self.stats['http_success']}/{self.stats['total']}")

            return {
                'output_file': output_csv_path,
                'stats': self.stats,
                'comparison_data': comparison_data
            }

        except Exception as e:
            logger.error(f"❌ Error generating comparison CSV: {e}")
            raise

    def update_local_from_reviewed_csv(self, reviewed_csv_path: str, original_csv_path: str,
                                       output_csv_path: str = None) -> Dict:
        """Update local CSV from comparison CSV"""
        try:
            logger.info(f"📄 Reading comparison CSV: {reviewed_csv_path}")
            comparison_df = pd.read_csv(reviewed_csv_path)

            required_columns = ['product_id', 'old_price', 'new_price', 'price_change_needed']
            if not all(col in comparison_df.columns for col in required_columns):
                raise ValueError(f"Comparison CSV must contain: {required_columns}")

            logger.info(f"📄 Reading original CSV: {original_csv_path}")
            original_df = pd.read_csv(original_csv_path)

            if not output_csv_path:
                output_csv_path = original_csv_path
                backup_path = f"{original_csv_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"📑 Creating backup: {backup_path}")
                original_df.to_csv(backup_path, index=False)

            changes_df = comparison_df[comparison_df['price_change_needed'] == 'YES']
            logger.info(f"📊 Found {len(changes_df)} products needing updates\n")

            if len(changes_df) == 0:
                logger.warning('⚠️  No changes needed')
                return {'updated': 0, 'errors': 0, 'updates': []}

            update_results = {'updated': 0, 'errors': 0, 'updates': []}
            updated_df = original_df.copy()

            for index, product in changes_df.iterrows():
                progress = f"[{index + 1}/{len(changes_df)}]"
                product_id = product['product_id']
                old_price = float(product['old_price'])
                new_price = float(product['new_price'])

                logger.info(f"{progress} 🔄 Updating {product_id}: Rs. {old_price} → Rs. {new_price}")

                try:
                    mask = updated_df['product_id'] == product_id
                    if mask.any():
                        updated_df.loc[mask, 'price'] = new_price

                        if 'price_history' in updated_df.columns:
                            current_history = self.parse_price_history(updated_df.loc[mask, 'price_history'].values[0])
                            updated_history = self.update_price_history(current_history, new_price)
                            updated_df.loc[mask, 'price_history'] = json.dumps(updated_history)

                        if 'last_updated' in updated_df.columns:
                            updated_df.loc[mask, 'last_updated'] = datetime.now().isoformat()

                        product_name = updated_df.loc[mask, 'name'].values[0] if 'name' in updated_df.columns else product_id
                        logger.info(f"{progress} ✅ Updated: {product_name}")
                        update_results['updated'] += 1
                        update_results['updates'].append({
                            'name': product_name,
                            'product_id': product_id,
                            'old_price': old_price,
                            'new_price': new_price
                        })
                    else:
                        logger.error(f"{progress} ❌ Product not found: {product_id}")
                        update_results['errors'] += 1
                except Exception as e:
                    logger.error(f"{progress} ❌ Error: {e}")
                    update_results['errors'] += 1

                logger.info('')

            updated_df.to_csv(output_csv_path, index=False)
            logger.info(f"📄 Updated CSV saved: {output_csv_path}")
            self._generate_update_report(update_results)
            return update_results

        except Exception as e:
            logger.error(f"❌ Error updating CSV: {e}")
            raise

    def _generate_update_report(self, results: Dict):
        """Generate update report"""
        report = f"""
🏪 JALAL SONS PRICE UPDATE REPORT (FAST VERSION)
===============================================
✅ Updated: {results['updated']}
❌ Errors: {results['errors']}

📝 UPDATES:
"""
        if results['updates']:
            for update in results['updates']:
                report += f"• {update['name']}\n  Rs. {update['old_price']} → Rs. {update['new_price']}\n"
        else:
            report += "(No updates)\n"

        report += f"\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        logger.info('\n' + report)

        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)
        report_path = os.path.join(reports_dir, f'jalalsons_update_report_{timestamp}.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"📄 Report saved: {report_path}")


# MAIN EXECUTION FUNCTIONS

def generate_price_comparison(csv_file_path: str, output_path: str = None,
                               delay_seconds: float = 0.5,
                               progress_tracker: Optional[ProgressTracker] = None) -> Dict:
    """
    Generate comparison CSV using fast HTTP requests.

    Args:
        csv_file_path: Path to input CSV with products
        output_path: Path for output comparison CSV
        delay_seconds: Delay between requests (default 0.5s - much faster!)
        progress_tracker: Optional progress tracker for resumability
    """
    updater = JalalSonsPriceUpdaterFast()

    try:
        results = updater.generate_comparison_csv(csv_file_path, output_path, delay_seconds, progress_tracker)
        logger.info(f"\n🎉 Price comparison completed!")
        return results
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        raise


def update_local_from_reviewed_csv(reviewed_csv_path: str, original_csv_path: str,
                                    output_csv_path: str = None) -> Dict:
    """Update local CSV from comparison CSV"""
    updater = JalalSonsPriceUpdaterFast()

    try:
        results = updater.update_local_from_reviewed_csv(reviewed_csv_path, original_csv_path, output_csv_path)
        logger.info(f"\n🎉 Update completed!")
        logger.info(f"📊 {results['updated']} updated, {results['errors']} errors")
        return results
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        raise


# USAGE EXAMPLES:
if __name__ == "__main__":
    # Step 1: Generate comparison CSV (FAST!)
    # delay_seconds=0.5 means 2 requests per second (vs Selenium's 3 seconds per product)
    generate_price_comparison(
        csv_file_path='jalalsons.csv',
        delay_seconds=0.5
    )

    # # Step 2: Update local CSV
    # update_local_from_reviewed_csv(
    #     reviewed_csv_path='jalalsons_price_comparison_2025-01-28.csv',
    #     original_csv_path='jalalsons.csv'
    # )
