"""
OPTIMIZED Metro Price Updater - Using HTTP Requests instead of Selenium

Speed improvement: ~10-20x faster than Selenium version
Metro has prices in JSON: {"id":387468,"price":905,"sell_price":null,...}
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from progress_tracker import ProgressTracker

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetroPriceUpdaterFast:
    """Optimized Metro price updater using HTTP requests."""

    def __init__(self):
        self.base_url = "https://www.metro-online.pk"
        self.store_id = "Metro"
        self.stats = {'total': 0, 'processed': 0, 'price_changes': 0, 'errors': 0, 'unchanged': 0}

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def _fetch_page(self, url: str, timeout: int = 10) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.debug(f"   Request failed: {e}")
            return None

    def extract_price_from_json_scripts(self, html: str) -> Optional[float]:
        """
        Metro has price data in script tags with format:
        {"id":387468,"price":905,"sell_price":null,...}
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script')

            for script in scripts:
                if script.string:
                    # Find JSON objects with price field
                    # Pattern: {"price":905} or "price":905
                    matches = re.findall(r'\{[^{}]*"price"\s*:\s*(\d+\.?\d*)[^{}]*\}', script.string)
                    if matches:
                        for match in matches:
                            try:
                                price = float(match)
                                if 0 < price < 1000000:
                                    return price
                            except ValueError:
                                continue

                    # Also try to find and parse complete JSON objects
                    json_patterns = re.findall(r'\{[^{}]*(?:price|sell_price|sale_price)[^{}]*\}', script.string)
                    for pattern in json_patterns:
                        try:
                            data = json.loads(pattern)
                            # Check various price fields
                            for key in ['price', 'sell_price', 'sale_price', 'gross_sell_price']:
                                if key in data and data[key]:
                                    price = float(data[key])
                                    if 0 < price < 1000000:
                                        return price
                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue

        except Exception as e:
            logger.debug(f"   JSON parsing error: {e}")

        return None

    def extract_price_from_next_data(self, html: str) -> Optional[float]:
        """Extract from __NEXT_DATA__ script tag."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            next_data = soup.find('script', id='__NEXT_DATA__')
            if next_data:
                data = json.loads(next_data.string)

                def find_price(obj, depth=0):
                    if depth > 15:
                        return None
                    if isinstance(obj, dict):
                        for key in ['price', 'sellingPrice', 'finalPrice', 'amount', 'value']:
                            if key in obj:
                                val = obj[key]
                                if isinstance(val, (int, float)):
                                    if 0 < val < 1000000:
                                        return float(val)
                                elif isinstance(val, str):
                                    match = re.search(r'(\d+\.?\d*)', val.replace(',', ''))
                                    if match:
                                        p = float(match.group(1))
                                        if 0 < p < 1000000:
                                            return p
                        for v in obj.values():
                            result = find_price(v, depth + 1)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_price(item, depth + 1)
                            if result:
                                return result
                    return None

                return find_price(data)

        except Exception as e:
            logger.debug(f"   __NEXT_DATA__ error: {e}")

        return None

    def extract_price_from_html_text(self, html: str) -> Optional[float]:
        """Fallback: extract price from HTML text patterns."""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Look for elements with price-related classes
            price_elements = soup.select('[class*="price"]')
            for elem in price_elements:
                text = elem.get_text(strip=True)
                # Pattern: Rs 905, PKR 905, 905
                match = re.search(r'(?:Rs\.?|PKR)?\s*(\d{1,5}[,\d]*\.?\d*)', text)
                if match:
                    price_str = match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        if 0 < price < 100000:
                            return price
                    except ValueError:
                        continue

        except Exception as e:
            logger.debug(f"   HTML text extraction error: {e}")

        return None

    def extract_price_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract price from Metro product page."""
        try:
            logger.info(f"   🌐 Fetching: {url}")
            html = self._fetch_page(url)

            if not html:
                logger.warning(f"   ❌ Failed to fetch")
                return None

            # Try multiple strategies
            price = self.extract_price_from_json_scripts(html)
            source = "JSON script"

            if price is None:
                price = self.extract_price_from_next_data(html)
                source = "__NEXT_DATA__"

            if price is None:
                price = self.extract_price_from_html_text(html)
                source = "HTML text"

            if price:
                logger.info(f"   💰 Found price: Rs. {price} (via {source})")
                return {
                    'current_price': price,
                    'original_price': None,
                    'source_info': {'method': 'HTTP + ' + source}
                }
            else:
                logger.warning(f"   ❌ Could not extract price")
                return None

        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            return None

    def parse_price_history(self, data) -> List[Dict]:
        try:
            if pd.isna(data) or data == '':
                return []
            if isinstance(data, str) and (data.startswith('[') or data.startswith('{')):
                return json.loads(data)
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def create_price_history_entry(self, price: float, is_current: bool = False) -> Dict:
        return {'price': price, 'is_current': is_current, 'timestamp': datetime.now().isoformat()}

    def update_price_history(self, history: List[Dict], new_price: float) -> List[Dict]:
        updated = []
        for entry in history:
            e = entry.copy()
            e['is_current'] = False
            updated.append(e)
        updated.append(self.create_price_history_entry(new_price, True))
        return updated

    def generate_comparison_csv(self, input_csv_path: str, output_csv_path: str = None,
                                delay_seconds: float = 0.5, progress_tracker: Optional[ProgressTracker] = None) -> Dict:
        try:
            if not output_csv_path:
                timestamp = datetime.now().strftime('%Y-%m-%d')
                output_csv_path = f'metro_price_comparison_{timestamp}.csv'

            logger.info(f"📄 Reading CSV: {input_csv_path}")
            df = pd.read_csv(input_csv_path)
            self.stats['total'] = len(df)
            logger.info(f"📊 Found {self.stats['total']} products\n")

            comparison_data = []

            if progress_tracker:
                processed_ids = progress_tracker.get_processed_ids()
                if processed_ids:
                    df = df[~df['product_id'].astype(str).isin(processed_ids)]
                    logger.info(f"📂 Skipping {len(processed_ids)} processed products")

            for index, product in df.iterrows():
                progress = f"[{index + 1}/{self.stats['total']}]"
                product_name = product.get('name', 'Unknown')

                logger.info(f"{progress} 🔍 Checking: {product_name}")

                comparison_row = {
                    'product_id': product.get('product_id'),
                    'old_price': product.get('price'),
                    'new_price': None,
                    'price_change_needed': 'NO'
                }

                if pd.isna(product.get('original_url')) or not product.get('original_url'):
                    logger.warning(f"{progress} ⏭️  No URL")
                    comparison_row['price_change_needed'] = 'ERROR - No URL'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', error_message='No URL')
                    continue

                csv_price = product.get('price')
                if pd.isna(csv_price) or csv_price <= 0:
                    logger.warning(f"{progress} ⏭️  Invalid price")
                    comparison_row['price_change_needed'] = 'ERROR - Invalid Price'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', error_message='Invalid Price')
                    continue

                logger.info(f"   📋 CSV Price: Rs. {csv_price}")

                website_data = self.extract_price_from_page(product['original_url'])

                if not website_data:
                    logger.warning(f"{progress} ❌ Fetch failed")
                    comparison_row['price_change_needed'] = 'ERROR - Failed'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', old_price=csv_price)
                elif not website_data.get('current_price'):
                    logger.warning(f"{progress} ❌ No price found")
                    comparison_row['price_change_needed'] = 'ERROR - Not found'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    if progress_tracker:
                        progress_tracker.save_progress(product.get('product_id'), 'ERROR', old_price=csv_price)
                else:
                    website_price = website_data['current_price']
                    diff = website_price - csv_price
                    comparison_row['new_price'] = website_price

                    if abs(diff) < 0.01:
                        logger.info(f"{progress} ✅ Match")
                        comparison_row['price_change_needed'] = 'NO'
                        self.stats['unchanged'] += 1
                        if progress_tracker:
                            progress_tracker.save_progress(product.get('product_id'), 'NO_CHANGE', old_price=csv_price, new_price=website_price)
                    else:
                        logger.info(f"{progress} 🔄 Diff: Rs. {diff:.2f}")
                        comparison_row['price_change_needed'] = 'YES'
                        self.stats['price_changes'] += 1
                        if progress_tracker:
                            progress_tracker.save_progress(product.get('product_id'), 'SUCCESS', old_price=csv_price, new_price=website_price)

                    comparison_data.append(comparison_row)
                    self.stats['processed'] += 1

                logger.info('')
                if index < len(df) - 1:
                    time.sleep(delay_seconds)

            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_csv(output_csv_path, index=False)

            logger.info(f"\n✅ Saved: {output_csv_path}")
            logger.info(f"📊 {self.stats['processed']} checked, {self.stats['price_changes']} changes, {self.stats['unchanged']} unchanged, {self.stats['errors']} errors")

            return {'output_file': output_csv_path, 'stats': self.stats, 'comparison_data': comparison_data}

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise

    def update_local_from_reviewed_csv(self, reviewed_csv_path: str, original_csv_path: str, output_csv_path: str = None) -> Dict:
        try:
            logger.info(f"📄 Reading comparison CSV")
            comparison_df = pd.read_csv(reviewed_csv_path)

            required = ['product_id', 'old_price', 'new_price', 'price_change_needed']
            if not all(col in comparison_df.columns for col in required):
                raise ValueError(f"Missing columns: {required}")

            logger.info(f"📄 Reading original CSV")
            original_df = pd.read_csv(original_csv_path)

            if not output_csv_path:
                output_csv_path = original_csv_path
                backup = f"{original_csv_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"📑 Backup: {backup}")
                original_df.to_csv(backup, index=False)

            changes_df = comparison_df[comparison_df['price_change_needed'] == 'YES']
            logger.info(f"📊 {len(changes_df)} updates needed\n")

            if len(changes_df) == 0:
                return {'updated': 0, 'errors': 0, 'updates': []}

            results = {'updated': 0, 'errors': 0, 'updates': []}
            updated_df = original_df.copy()

            for index, product in changes_df.iterrows():
                progress = f"[{index + 1}/{len(changes_df)}]"
                product_id = product['product_id']
                old_price = float(product['old_price'])
                new_price = float(product['new_price'])

                logger.info(f"{progress} 🔄 {product_id}: Rs. {old_price} → Rs. {new_price}")

                try:
                    mask = updated_df['product_id'] == product_id
                    if mask.any():
                        updated_df.loc[mask, 'price'] = new_price

                        if 'price_history' in updated_df.columns:
                            history = self.parse_price_history(updated_df.loc[mask, 'price_history'].values[0])
                            updated_df.loc[mask, 'price_history'] = json.dumps(self.update_price_history(history, new_price))

                        if 'last_updated' in updated_df.columns:
                            updated_df.loc[mask, 'last_updated'] = datetime.now().isoformat()

                        name = updated_df.loc[mask, 'name'].values[0] if 'name' in updated_df.columns else product_id
                        logger.info(f"{progress} ✅ {name}")
                        results['updated'] += 1
                        results['updates'].append({'name': name, 'product_id': product_id, 'old_price': old_price, 'new_price': new_price})
                    else:
                        logger.error(f"{progress} ❌ Not found")
                        results['errors'] += 1
                except Exception as e:
                    logger.error(f"{progress} ❌ {e}")
                    results['errors'] += 1

                logger.info('')

            updated_df.to_csv(output_csv_path, index=False)
            logger.info(f"📄 Saved: {output_csv_path}")
            return results

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise

    def _generate_update_report(self, results: Dict):
        report = f"""
🏪 METRO PRICE UPDATE REPORT (FAST)
===================================
✅ Updated: {results['updated']}
❌ Errors: {results['errors']}
🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        logger.info('\n' + report)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('reports', exist_ok=True)
        with open(f"reports/metro_update_report_{timestamp}.txt", 'w') as f:
            f.write(report)


def generate_price_comparison(csv_file_path: str, output_path: str = None,
                               delay_seconds: float = 0.5,
                               progress_tracker: Optional[ProgressTracker] = None) -> Dict:
    updater = MetroPriceUpdaterFast()
    try:
        return updater.generate_comparison_csv(csv_file_path, output_path, delay_seconds, progress_tracker)
    except Exception as e:
        logger.error(f"💥 {e}")
        raise


def update_local_from_reviewed_csv(reviewed_csv_path: str, original_csv_path: str,
                                    output_csv_path: str = None) -> Dict:
    updater = MetroPriceUpdaterFast()
    try:
        return updater.update_local_from_reviewed_csv(reviewed_csv_path, original_csv_path, output_csv_path)
    except Exception as e:
        logger.error(f"💥 {e}")
        raise


if __name__ == "__main__":
    generate_price_comparison('metro.csv', delay_seconds=0.5)
