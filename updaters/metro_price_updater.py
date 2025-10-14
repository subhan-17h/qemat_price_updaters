#type: ignore
import pandas as pd
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetroPriceUpdater:
    def __init__(self, headless: bool = False):
        """
        Initialize the Metro price updater (Local CSV only version)
        
        Args:
            headless (bool): Run browser in headless mode
        """
        self.base_url = "https://www.metro-online.pk"
        self.store_id = "Metro"
        self.headless = headless
        self.driver = None
        
        # Statistics tracking
        self.stats = {
            'total': 0,
            'processed': 0,
            'price_changes': 0,
            'errors': 0,
            'unchanged': 0,
            'results': []
        }
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            
            # Ubuntu-specific Chrome options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Chrome driver initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            return False
    
    def _test_website_connection(self) -> bool:
        """Send a test request to the base URL to ensure the website is responsive"""
        try:
            logger.info(f"🔍 Testing website connection to {self.base_url}...")
            self.driver.set_page_load_timeout(15)
            
            try:
                self.driver.get(self.base_url)
                time.sleep(2)  # Wait for page to load
                
                # Check if page loaded successfully (basic check)
                if "metro" in self.driver.title.lower() or "metro" in self.driver.current_url.lower():
                    logger.info("✅ Website connection test successful")
                    return True
                else:
                    logger.warning(f"⚠️  Website connection test completed but page may not have loaded correctly")
                    logger.info(f"   Page title: {self.driver.title}")
                    return True  # Still return True as we got some response
                    
            except Exception as e:
                logger.warning(f"⚠️  Website connection test failed: {e}")
                logger.info("   Will continue with product scraping anyway...")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  Error during website connection test: {e}")
            return False
        
    def extract_price_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract current price from Metro website"""
        try:
            logger.info(f"   🌐 Visiting: {url}")

            # Set page load timeout to 10 seconds
            self.driver.set_page_load_timeout(10)
            
            try:
                self.driver.get(url)
            except Exception as timeout_error:
                logger.error(f"   ⏱️ Page load timeout after 10 seconds: {url}")
                return None
            
            # Wait for page to load
            time.sleep(3)
            
            # Specific selectors for Metro website product detail page
            metro_selectors = [
                # Primary selector based on the provided HTML structure
                ".CategoryGrid_product_details_price__dNQQQ",
                # Alternative selectors for different page layouts
                "p.CategoryGrid_product_details_price__dNQQQ",
                # Fallback selectors for Metro
                ".product_details_price",
                ".product-price",
                ".price-current",
                ".current-price",
                # Generic price selectors
                "[class*='price']",
                ".price"
            ]
            
            # Try each selector
            for selector in metro_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            # Handle input field differently
                            if element.tag_name.lower() == 'input':
                                price_text = element.get_attribute('value')
                            else:
                                price_text = element.text.strip()
                            
                            if price_text:
                                logger.info(f"Found price with selector '{selector}': {price_text}")
                                
                                # Clean the price text (Metro uses "Rs." format)
                                cleaned_price = price_text.replace('Rs.', '').replace('Rs', '').replace('PKR', '').replace(',', '').strip()
                                
                                if cleaned_price:
                                    try:
                                        price_value = float(cleaned_price)
                                        if price_value > 0:
                                            logger.info(f"   💰 Found price: Rs. {price_value} (using selector: {selector})")
                                            
                                            return {
                                                'current_price': price_value,
                                                'original_price': None,  # Jalal Sons might not show original price
                                                'source_info': {
                                                    'selector': selector,
                                                    'original_text': price_text,
                                                    'cleaned_text': cleaned_price
                                                },
                                                'is_sale': False
                                            }
                                    except ValueError:
                                        logger.debug(f"Could not convert price to float: {cleaned_price}")
                except Exception as e:
                    logger.debug(f"Error with selector '{selector}': {e}")
            
            # If specific selectors don't work, try broader approach
            fallback_selectors = [
                ".price",
                ".amount",
                "[data-price]",
                ".product-price",
                ".current-price",
                ".selling-price",
                ".final-price"
            ]
            
            found_prices = []
            source_info = {}
            
            for selector in fallback_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        # Handle different element types
                        if element.tag_name.lower() == 'input':
                            price_text = element.get_attribute('value')
                        else:
                            price_text = element.text.strip()
                            
                        if price_text:
                            logger.debug(f"Found price text with fallback selector '{selector}': {price_text}")
                            cleaned_price = price_text.replace('Rs.', '').replace('Rs', '').replace('PKR', '').replace(',', '').strip()
                            
                            if cleaned_price:
                                try:
                                    price_value = float(cleaned_price)
                                    if price_value > 0:
                                        found_prices.append(price_value)
                                        source_info[price_value] = {
                                            'selector': selector,
                                            'original_text': price_text,
                                            'cleaned_text': cleaned_price
                                        }
                                except ValueError:
                                    logger.debug(f"Could not convert price to float: {cleaned_price}")
                except Exception as e:
                    logger.debug(f"Error with fallback selector '{selector}': {e}")
                    continue
            
            if found_prices:
                # Return the most reasonable price (usually the lowest for current price)
                current_price = min(found_prices)
                
                logger.info(f"   💰 Found price: Rs. {current_price} (using fallback selector: {source_info[current_price]['selector']})")
                
                return {
                    'current_price': current_price,
                    'original_price': max(found_prices) if len(found_prices) > 1 else None,
                    'all_prices': found_prices,
                    'source_info': source_info[current_price],
                    'total_found': len(found_prices)
                }
            else:
                logger.warning(f"   ❌ No price found on page")
                return None
                
        except Exception as e:
            logger.error(f"   ❌ Error extracting price from {url}: {e}")
            return None
    
    def parse_price_history(self, price_history_data) -> List[Dict]:
        """Parse price history from CSV data"""
        try:
            if pd.isna(price_history_data) or price_history_data == '':
                return []
            
            # Handle different possible formats
            if isinstance(price_history_data, str):
                # Try to parse as JSON if it looks like JSON
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
        # Set all existing entries to is_current: false
        updated_history = []
        for entry in current_history:
            updated_entry = entry.copy()
            updated_entry['is_current'] = False
            updated_history.append(updated_entry)
        
        # Add new entry as current
        updated_history.append(self.create_price_history_entry(new_price, True))
        
        return updated_history
    
    def generate_comparison_csv(self, input_csv_path: str, output_csv_path: str = None, delay_seconds: int = 3) -> Dict:
        """Generate comparison CSV for manual review"""
        try:
            if not output_csv_path:
                timestamp = datetime.now().strftime('%Y-%m-%d')
                output_csv_path = f'metro_price_comparison_{timestamp}.csv'
            
            # Initialize browser
            if not self._setup_driver():
                raise Exception("Failed to initialize browser")
            
            logger.info(f"📄 Reading CSV file: {input_csv_path}")
            df = pd.read_csv(input_csv_path)
            
            self.stats['total'] = len(df)
            logger.info(f"📊 Found {self.stats['total']} products to check\n")
            
            # Test website connection before processing products
            self._test_website_connection()
            
            comparison_data = []
            
            for index, product in df.iterrows():
                progress = f"[{index + 1}/{self.stats['total']}]"
                product_name = product.get('name', 'Unknown Product')
                
                logger.info(f"{progress} 🔍 Checking: {product_name}")
                
                # Create base comparison row
                comparison_row = {
                    'product_id': product.get('product_id'),
                    'old_price': product.get('price'),
                    'new_price': None,
                    'price_change_needed': 'NO'
                }
                
                # Parse current price history
                current_price_history = self.parse_price_history(product.get('price_history'))
                
                # Skip if no URL
                if pd.isna(product.get('original_url')) or not product.get('original_url'):
                    logger.warning(f"{progress} ⏭️  Skipping - No original_url provided")
                    comparison_row['price_change_needed'] = 'ERROR - No URL'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    continue
                
                csv_price = product.get('price')
                if pd.isna(csv_price) or csv_price <= 0:
                    logger.warning(f"{progress} ⏭️  Skipping - Invalid CSV price: {csv_price}")
                    comparison_row['price_change_needed'] = 'ERROR - Invalid Price'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                    continue
                
                logger.info(f"   📋 CSV Price: Rs. {csv_price}")
                logger.info(f"   📚 Price History: {len(current_price_history)} entries")
                
                # Get current price from website
                website_data = self.extract_price_from_page(product['original_url'])
                
                if not website_data:
                    logger.warning(f"{progress} ❌ Could not fetch website price (possible timeout)")
                    comparison_row['price_change_needed'] = 'ERROR - Page timeout or failed to load'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                elif not website_data.get('current_price'):
                    logger.warning(f"{progress} ❌ Could not extract price from page")
                    comparison_row['price_change_needed'] = 'ERROR - Price not found on page'
                    comparison_data.append(comparison_row)
                    self.stats['errors'] += 1
                else:
                    website_price = website_data['current_price']
                    price_difference = website_price - csv_price
                    
                    # Update comparison row with website data
                    comparison_row['new_price'] = website_price
                    
                    # Determine if price change is needed
                    if abs(price_difference) < 0.01:
                        logger.info(f"{progress} ✅ Prices match - No update needed")
                        comparison_row['price_change_needed'] = 'NO'
                        self.stats['unchanged'] += 1
                    else:
                        logger.info(f"{progress} 🔄 Price difference: Rs. {price_difference:.2f}")
                        logger.info(f"   📋 CSV: Rs. {csv_price}")
                        logger.info(f"   🌐 Website: Rs. {website_price}")
                        comparison_row['price_change_needed'] = 'YES'
                        self.stats['price_changes'] += 1
                    
                    comparison_data.append(comparison_row)
                    self.stats['processed'] += 1
                
                logger.info('')
                
                # Rate limiting (longer delay for Metro)
                if index < len(df) - 1:
                    logger.info(f"   ⏳ Waiting {delay_seconds}s before next request...")
                    time.sleep(delay_seconds)
            
            # Save comparison CSV
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_csv(output_csv_path, index=False)
            
            logger.info(f"\n✅ Comparison CSV generated: {output_csv_path}")
            logger.info(f"📊 Summary: {self.stats['processed']} checked, {self.stats['price_changes']} need updates, {self.stats['unchanged']} unchanged, {self.stats['errors']} errors")
            
            logger.info(f"\n📝 NEXT STEPS:")
            logger.info(f"1. Open {output_csv_path}")
            logger.info(f"2. Review products where 'price_change_needed' = 'YES'")
            logger.info(f"3. Run update_local_from_reviewed_csv('{output_csv_path}', 'your_original.csv') to apply changes")
            
            return {
                'output_file': output_csv_path,
                'stats': self.stats,
                'comparison_data': comparison_data
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating comparison CSV: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info('🔚 Browser closed')
    
    def update_local_from_reviewed_csv(self, reviewed_csv_path: str, original_csv_path: str, output_csv_path: str = None) -> Dict:
        """Update local CSV from comparison CSV
        
        Args:
            reviewed_csv_path (str): Path to the comparison CSV with 4 columns
            original_csv_path (str): Path to the original products CSV to update
            output_csv_path (str): Output path for updated CSV (defaults to overwriting original)
        """
        try:
            logger.info(f"📄 Reading comparison CSV: {reviewed_csv_path}")
            comparison_df = pd.read_csv(reviewed_csv_path)
            
            # Verify required columns exist
            required_columns = ['product_id', 'old_price', 'new_price', 'price_change_needed']
            if not all(col in comparison_df.columns for col in required_columns):
                raise ValueError(f"Comparison CSV must contain these columns: {required_columns}")
            
            # Read the original products CSV
            logger.info(f"📄 Reading original products CSV: {original_csv_path}")
            original_df = pd.read_csv(original_csv_path)
            
            # Create output path if not provided (default to overwriting the original)
            if not output_csv_path:
                output_csv_path = original_csv_path
                # Create a backup of the original file
                backup_path = f"{original_csv_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"📑 Creating backup of original file: {backup_path}")
                original_df.to_csv(backup_path, index=False)
            
            # Filter for entries that need price changes (YES only)
            changes_needed_df = comparison_df[comparison_df['price_change_needed'] == 'YES']
            
            logger.info(f"📊 Found {len(changes_needed_df)} products that need price updates\n")
            
            if len(changes_needed_df) == 0:
                logger.warning('⚠️  No price changes needed. Exiting.')
                return {'updated': 0, 'errors': 0, 'updates': []}
            
            update_results = {
                'updated': 0,
                'errors': 0,
                'updates': []
            }
            
            # Create a copy of the original dataframe to update
            updated_df = original_df.copy()
            
            for index, product in changes_needed_df.iterrows():
                progress = f"[{index + 1}/{len(changes_needed_df)}]"
                
                product_id = product['product_id']
                old_price = float(product['old_price'])
                new_price = float(product['new_price'])
                
                logger.info(f"{progress} 🔄 Updating product: {product_id}")
                logger.info(f"   💰 {old_price} → {new_price}")
                
                try:
                    # Find the matching row in the original dataframe
                    mask = updated_df['product_id'] == product_id
                    if mask.any():
                        # Update the price
                        updated_df.loc[mask, 'price'] = new_price
                        
                        # Update price_history if it exists
                        if 'price_history' in updated_df.columns:
                            # Parse current price history
                            current_price_history = self.parse_price_history(updated_df.loc[mask, 'price_history'].values[0])
                            # Update price history
                            updated_price_history = self.update_price_history(current_price_history, new_price)
                            updated_df.loc[mask, 'price_history'] = json.dumps(updated_price_history)
                        
                        # Update last_updated if it exists
                        if 'last_updated' in updated_df.columns:
                            updated_df.loc[mask, 'last_updated'] = datetime.now().isoformat()
                        
                        # Get product name if available
                        product_name = updated_df.loc[mask, 'name'].values[0] if 'name' in updated_df.columns else f"Product {product_id}"
                        
                        logger.info(f"{progress} ✅ Successfully updated: {product_name}")
                        update_results['updated'] += 1
                        update_results['updates'].append({
                            'name': product_name,
                            'product_id': product_id,
                            'old_price': old_price,
                            'new_price': new_price,
                            'price_history_entries': len(current_price_history) + 1 if 'price_history' in updated_df.columns else 1
                        })
                    else:
                        logger.error(f"{progress} ❌ Could not find product with ID {product_id} in original CSV")
                        update_results['errors'] += 1
                except Exception as e:
                    logger.error(f"{progress} ❌ Error updating data for product {product_id}: {e}")
                    update_results['errors'] += 1
                
                logger.info('')
            
            # Save the updated dataframe
            updated_df.to_csv(output_csv_path, index=False)
            logger.info(f"📄 Updated CSV saved to: {output_csv_path}")
            
            self._generate_update_report(update_results)
            return update_results
            
        except Exception as e:
            logger.error(f"❌ Error updating local CSV: {e}")
            raise
    
    def _generate_update_report(self, results: Dict):
        """Generate update report"""
        report = f"""
🏪 METRO PRICE UPDATE REPORT
============================
✅ Successfully Updated: {results['updated']}
❌ Errors/Skipped: {results['errors']}

📝 PRICE UPDATES MADE:
"""
        
        if results['updates']:
            for update in results['updates']:
                report += f"""• {update['name']}
  Price: Rs. {update['old_price']} → Rs. {update['new_price']}
  Product ID: {update['product_id']}
  Price History Entries: {update['price_history_entries']}
"""
        else:
            report += "(No updates were made)\n"
        
        report += f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        logger.info('\n' + report)
        
        # Save report to file in reports folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)  # Create reports directory if it doesn't exist
        report_filename = f'metro_update_report_{timestamp}.txt'
        report_path = os.path.join(reports_dir, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"📄 Report saved to: {report_path}")


# MAIN EXECUTION FUNCTIONS

def generate_price_comparison(csv_file_path: str, output_path: str = None, delay_seconds: int = 3) -> Dict:
    """Generate comparison CSV for manual review"""
    updater = MetroPriceUpdater(headless=False)
    
    try:
        results = updater.generate_comparison_csv(csv_file_path, output_path, delay_seconds)
        logger.info(f"\n🎉 Price comparison completed!")
        return results
    except Exception as e:
        logger.error(f"💥 Error generating comparison: {e}")
        raise

def update_local_from_reviewed_csv(reviewed_csv_path: str, original_csv_path: str, output_csv_path: str = None) -> Dict:
    """Update local CSV from comparison CSV"""
    updater = MetroPriceUpdater(headless=False)
    
    try:
        results = updater.update_local_from_reviewed_csv(reviewed_csv_path, original_csv_path, output_csv_path)
        logger.info(f"\n🎉 Local CSV update completed!")
        logger.info(f"📊 Summary: {results['updated']} updated, {results['errors']} errors")
        return results
    except Exception as e:
        logger.error(f"💥 Error updating local CSV: {e}")
        raise



# USAGE EXAMPLES:
if __name__ == "__main__":
    # Step 1: Generate comparison CSV
    # This will create a CSV with columns: product_id, old_price, new_price, price_change_needed
    generate_price_comparison('2.csv')
    
    # # Step 2: Update local CSV with changes
    # # This will update only products where price_change_needed = 'YES'
    # update_local_from_reviewed_csv(
    #     reviewed_csv_path='metro_price_comparison_2025-10-04.csv',
    #     original_csv_path='metro_products.csv',
    #     output_csv_path='updated_metro_products.csv'  # Optional: defaults to overwriting original
    # )